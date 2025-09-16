from collections.abc import Iterable, Mapping
from itertools import islice, product
from random import shuffle
from typing import Any, Dict, Set, cast

from faker import Faker
from sqlalchemy import Column
from sqlalchemy.orm import Session
from sqlalchemy.sql.schema import Table

from .constants import TYPE_DEFAULTS, TypeDefaults
from .dependency_graph import DependencyGraph
from .primary_keys import PrimaryKeys
from .seed import Seed
from .seeded_column import SeededColumnMixin
from .types import SeedPlan, UniqueValues


class SeededModel:
    def __init__(
        self,
        model: type[Any],
        nb_of_rows_to_seed: int,
        session: Session,
        seed_plan: SeedPlan,
    ) -> None:
        self.is_link_table = False
        table = getattr(model, "__table__", None)
        if table is None:
            raise ValueError(f"Model {model.__name__} has no __table__ attribute")
        self.table = cast(Table, table)
        self.base_model: type[Any] = model
        self.nb_of_rows_to_seed = nb_of_rows_to_seed
        self.name = model.__name__
        self.foreign_key_dependencies: Set[str] = set()
        self.columns: Dict[str, Column[Any]] = {col.name: col for col in self.table.columns}
        self.primary_keys: tuple[str, ...] = tuple(
            col.name for col in self.table.primary_key.columns
        )
        self.unique_columns: tuple[str, ...] = tuple(
            col.name for col in self.table.columns if col.unique
        )
        self.existing_ids: PrimaryKeys[Any] = PrimaryKeys(self.primary_keys)
        self.new_ids: PrimaryKeys[Any] = PrimaryKeys(self.primary_keys)

        dependency_graph = DependencyGraph()
        primary_foreign_keys: list[str] = []

        for column in self.table.columns:
            if column.primary_key and column.foreign_keys:
                primary_foreign_keys.append(column.name)

            # Extract dependencies (if any)
            dependencies = set()
            if hasattr(column, "seed") and isinstance(column.seed, Seed):
                dependencies = self.columns[column.name].seed.dependencies

            # Validate dependencies
            for dep in dependencies:
                if dep not in self.columns.keys():
                    raise ValueError(
                        f"Column '{self.columns[column.name].name}' \
                        declares dependency on unknown column '{dep}'"
                    )

            dependency_graph.add(column.name, dependencies)

            # If FK → add to FK dependency set
            if column.foreign_keys:
                fk = next(iter(column.foreign_keys))
                target_table = fk.column.table

                for seed_plan_model in seed_plan.keys():
                    if seed_plan_model.__table__ == target_table and seed_plan_model != model:
                        self.foreign_key_dependencies.add(seed_plan_model.__name__)
                        break

        if len(primary_foreign_keys) > len(self.primary_keys):
            raise ValueError(
                f"Mix of primary keys that are also foreign keys with regular primary \
                keys is not supported in model {self.name} "
            )

        if sorted(primary_foreign_keys) == sorted(self.primary_keys):
            self.is_link_table = True

        self.unique_values: UniqueValues = {col: set() for col in self.unique_columns}

        # Load existing rows
        query = session.query(
            *[getattr(model, col) for col in self.primary_keys + self.unique_columns]
        )

        self._process_query_result(query, new_data=False)

        self.columns_seed_order = dependency_graph.topological_sort()

    def _process_query_result(self, query: Iterable[Any], new_data: bool = False) -> None:
        id_target = self.new_ids if new_data else self.existing_ids
        for row in query:
            # Extract primary key values from model instances or Row objects
            pk_values: list[Any] = []
            for name in self.primary_keys:
                # Try getattr for model instances, then _mapping for Row objects
                value = getattr(row, name, None)
                if value is None and hasattr(row, "_mapping"):
                    value = row._mapping.get(name)
                if value is None:
                    raise ValueError(f"Missing primary key field '{name}' in row: {row}")
                pk_values.append(value)

            pk_tuple = tuple(pk_values)
            id_target.add(pk_tuple)

            # Handle unique columns
            for col_name in self.unique_columns:
                value = getattr(row, col_name, None)
                if value is None and hasattr(row, "_mapping"):
                    value = row._mapping.get(col_name)
                if value is not None:
                    self.unique_values[col_name].add(value)

    def get_fk_combinations(
        self, models: Mapping[str, "SeededModel"], n: int
    ) -> list[Dict[str, Any]]:
        """Return up to *n* deterministic FK‐value combinations.

        * Correct mapping: field order is driven by ``fk_targets``.
        * Scalable: uses an iterator over ``itertools.product`` and stops at *n*,
        so it never materialises the full Cartesian product.
        * Works when FK target tables have unequal row counts.
        """

        # ── 1. Collect PK-FK metadata ──────────────────────────────────────────────
        primary_fk_columns = [
            col for col in self.columns.values() if col.primary_key and col.foreign_keys
        ]
        if len(primary_fk_columns) <= 1:
            return []

        fk_targets: list[str] = []  # column names in *deterministic* order
        value_lists: list[list[Any]] = []  # values per FK column (may differ in length)

        for col in primary_fk_columns:
            if len(col.foreign_keys) != 1:
                raise ValueError(
                    f"Column '{col.name}' in model '{self.name}' has "
                    f"{len(col.foreign_keys)} foreign keys; expected exactly one."
                )
            fk = next(iter(col.foreign_keys))
            target_table = fk.column.table
            target_model = self.table_to_model(col, target_table, models)

            target_field = fk.column.name
            pk_data = models[target_model.name].new_ids  # PrimaryKeys object

            if not pk_data:
                raise ValueError(f"No new IDs for FK '{col.name}' -> '{target_table.name}'")

            ids = [pk[target_field] for pk in pk_data.dicts()]
            if not ids:
                raise ValueError(f"No '{target_field}' values found in '{target_table.name}'")

            fk_targets.append(col.name)
            value_lists.append(ids)

        # ── 2. Validate requested sample size ──────────────────────────────────────
        max_combos = 1
        for ids in value_lists:
            max_combos *= len(ids)
        if n > max_combos:
            raise ValueError(f"Requested {n} combos, but only {max_combos} possible.")

        # ── 3. Build the iterator and slice lazily ─────────────────────────────────
        combo_iter = (
            dict(zip(fk_targets, combo, strict=True)) for combo in product(*value_lists)
        )

        return list(islice(combo_iter, n))

    def table_to_model(
        self,
        column: Any,
        table: Table,
        models: Mapping[str, "SeededModel"],
    ) -> "SeededModel":
        target_model: "SeededModel" | None = None
        for model in models.values():
            if model.table == table:
                target_model = model
                break
        if target_model is None:
            raise ValueError(
                f"Target model with table {table} not found for Foreign Key {column.name}"
            )
        return target_model

    def fake_column(
        self,
        col_name: str,
        models: Mapping[str, "SeededModel"],
        faker: Faker,
        type_defaults: TypeDefaults,
        column_context: Dict[str, Any],
        pfk_combo: Mapping[str, Any] | None = None,
    ) -> Any:
        column = self.columns[col_name]

        # Skip autoincrement PKs
        if column.autoincrement is True:
            return None

        # Handle Primary keys that are also foreign keys, must use valid combination
        if column.foreign_keys and column.primary_key:
            if pfk_combo is None:
                raise ValueError(
                    f"No combination of foreign keys provided for column {column} "
                    f"in model {self.name}"
                )

            if col_name not in pfk_combo:
                raise ValueError(
                    f"Field '{col_name}' not found in primary key combination : {pfk_combo}"
                )

            return pfk_combo[col_name]

        if column.foreign_keys:
            # For now: assume single FK per column
            fk = next(iter(column.foreign_keys))
            target_table = fk.column.table
            target_model = self.table_to_model(column, target_table, models)

            # Pick random ID from models and extract the scalar value
            pk_mapping = models[target_model.name].new_ids.get_random()
            target_field = fk.column.name  # The referenced column name (e.g., 'id')
            return pk_mapping[target_field]

            # Pick random ID from models
            # return models[target_model.name].new_ids.get_random()

        # Unique values logic
        used_unique_values = None

        if column.unique is True:
            used_unique_values = self.unique_values[column.name]

        if issubclass(column.__class__, SeededColumnMixin) and column.seed is not None:
            return column.generate(
                faker=faker,
                column_context=column_context,
                used_unique_values=used_unique_values,
            )

        for base_type, seed in TYPE_DEFAULTS.items():
            if isinstance(column.type, base_type):
                if isinstance(seed, str):
                    seed = Seed(seed)
                return seed.generate(
                    faker=faker,
                    column_context=column_context,
                    used_unique_values=used_unique_values,
                )

        if column.default is not None:
            default_arg = getattr(column.default, "arg", None)
            if callable(default_arg):
                return default_arg()
            return default_arg

        if column.server_default:
            return None

        if column.nullable:
            return None

        raise ValueError(
            f"Not Null column {col_name} on model {self.name} doesn't have a way to resolve a fake \
            value (no autoincrement, default value or seed  )"
        )

    def fake_row(
        self,
        models: Mapping[str, "SeededModel"],
        faker: Faker,
        type_defaults: TypeDefaults,
        pfk_combo: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        column_context: Dict[str, Any] = {}
        row: Dict[str, Any] = {}

        for col_name in self.columns_seed_order:
            value = self.fake_column(
                col_name=col_name,
                models=models,
                faker=faker,
                type_defaults=type_defaults,
                column_context=column_context,
                pfk_combo=pfk_combo,
            )
            if self.columns[col_name].unique:
                self.unique_values[col_name].add(value)
            column_context[col_name] = value
            row[col_name] = value

        return row

    def fake_rows(
        self,
        n: int,
        models: Mapping[str, "SeededModel"],
        faker: Faker,
        type_defaults: TypeDefaults,
    ) -> list[Dict[str, Any]]:
        if self.is_link_table:
            pfk_possible_combinations = self.get_fk_combinations(models, n)

            shuffled_combinations = list(pfk_possible_combinations)
            shuffle(shuffled_combinations)
            rows = [
                self.fake_row(
                    models=models, faker=faker, type_defaults=type_defaults, pfk_combo=combo
                )
                for combo in shuffled_combinations[:n]
            ]

        else:
            rows = [
                self.fake_row(models=models, faker=faker, type_defaults=type_defaults)
                for _ in range(n)
            ]

        return rows
