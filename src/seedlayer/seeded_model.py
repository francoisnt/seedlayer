from collections.abc import Iterable, Mapping
from typing import Any

from faker import Faker
from sqlalchemy import Column
from sqlalchemy.sql.schema import Table

from .constants import TYPE_DEFAULTS, TypeDefaults
from .dependency_graph import DependencyGraph
from .fk_combination_generator import FKCombinationGenerator
from .primary_keys import PrimaryKeys
from .seed import Seed
from .seeded_column import SeededColumnMixin
from .types import SeedingPlan, UniqueValues


class SeededModel:
    """Container class for managing data seeding on a specific SQLAlchemy model."""

    def __init__(
        self,
        model: type[Any],
        nb_of_rows_to_seed: int,
        seed_plan: SeedingPlan,
    ) -> None:
        """Initialize the SeededModel with model details and seeding plan."""
        self.combination_generator: FKCombinationGenerator | None = None
        self.is_link_table = False

        if not hasattr(model, "__table__"):
            raise ValueError(f"Model {model.__name__} has no __table__ attribute")
        self.table: Table = model.__table__

        self.base_model: type[Any] = model
        self.nb_of_rows_to_seed = nb_of_rows_to_seed
        self.name = model.__name__
        self.foreign_key_dependencies: set[str] = set()
        self.columns: dict[str, Column[Any]] = {col.name: col for col in self.table.columns}
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

        self.columns_seed_order = dependency_graph.topological_sort()

    def load_existing(self, session: Any) -> None:
        """Load existing rows from the database for this model."""
        query = session.query(
            *[getattr(self.base_model, col) for col in self.primary_keys + self.unique_columns]
        )
        self._process_query_result(query, new_data=False)

    def _process_query_result(self, query: Iterable[Any], new_data: bool = False) -> None:
        """Process query results to load existing or newly generated data.

        Args:
            query: Iterable of row objects from the query.
            new_data: Whether the data is newly generated or existing.
        """
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

    def table_to_model(
        self,
        column: Any,
        table: Table,
        models: Mapping[str, "SeededModel"],
    ) -> "SeededModel":
        """Find the SeededModel corresponding to a given table."""
        target_model: SeededModel | None = None
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
        column_context: dict[str, Any],
        pfk_combo: Mapping[str, Any] | None = None,
    ) -> Any:
        """Generate a fake value for the specified column based on its type and constraints."""
        column = self.columns[col_name]

        # Skip autoincrement PKs
        if column.autoincrement is True:
            return None

        # Handle Primary keys that are also foreign keys, must use valid combination
        if column.foreign_keys and column.primary_key:
            return self._fake_primary_fk_column(column, col_name, pfk_combo)

        if column.foreign_keys:
            return self._fake_foreign_key_column(column, models, faker)

        return self._fake_regular_column(column, col_name, faker, column_context)

    def _fake_primary_fk_column(
        self, column: Column[Any], col_name: str, pfk_combo: Mapping[str, Any] | None
    ) -> Any:
        """Handle generation of primary-foreign key columns."""
        if pfk_combo is None:
            msg = (
                f"No combination of foreign keys provided for column {column} in model {self.name}"
            )
            raise ValueError(msg)

        if col_name not in pfk_combo:
            msg = f"Field '{col_name}' not found in primary key combination: {pfk_combo}"
            raise ValueError(msg)

        return pfk_combo[col_name]

    def _fake_foreign_key_column(
        self, column: Column[Any], models: Mapping[str, "SeededModel"], faker: Faker
    ) -> Any:
        """Handle generation of regular foreign key columns."""
        fk = next(iter(column.foreign_keys))
        target_table = fk.column.table
        target_model = self.table_to_model(column, target_table, models)

        # Pick random ID from models and extract the scalar value
        pk_mapping = models[target_model.name].new_ids.get_random(faker)
        target_field = fk.column.name  # The referenced column name (e.g., 'id')
        return pk_mapping[target_field]

    def _fake_regular_column(
        self,
        column: Column[Any],
        col_name: str,
        faker: Faker,
        column_context: dict[str, Any],
    ) -> Any:
        """Handle generation of regular (non-FK) columns."""
        # Unique values logic
        used_unique_values = self.unique_values[column.name] if column.unique else None

        # SeededColumnMixin takes precedence
        if issubclass(column.__class__, SeededColumnMixin) and column.seed is not None:
            return column.generate(
                faker=faker,
                column_context=column_context,
                used_unique_values=used_unique_values,
            )

        # Type-based defaults
        for base_type, seed in TYPE_DEFAULTS.items():
            if isinstance(column.type, base_type):
                if isinstance(seed, str):
                    seed = Seed(seed)
                return seed.generate(
                    faker=faker,
                    column_context=column_context,
                    used_unique_values=used_unique_values,
                )

        # Column defaults
        if column.default is not None:
            default_arg = getattr(column.default, "arg", None)
            if callable(default_arg):
                return default_arg()
            return default_arg

        # Fallbacks for nullable or server-default columns
        if column.server_default or column.nullable:
            return None

        # No fallback available for non-nullable column
        msg = (
            f"Non-nullable column '{col_name}' in model '{self.name}' has no generator: "
            "no seed, type default, or callable default found."
        )
        raise ValueError(msg)

    def fake_row(
        self,
        models: Mapping[str, "SeededModel"],
        faker: Faker,
        type_defaults: TypeDefaults,
        pfk_combo: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a fake row dictionary for the model."""
        column_context: dict[str, Any] = {}
        row: dict[str, Any] = {}

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
    ) -> list[dict[str, Any]]:
        """Generate a list of n fake row dictionaries for the model."""
        if self.is_link_table:
            if self.combination_generator is None:
                # faker generated seed for FKCombinationGenerator will be deterministic if faker is
                self.combination_generator = FKCombinationGenerator(
                    self, models, faker.random_int(min=0, max=2**32 - 1)
                )

            combos_to_use = self.combination_generator.get_next_batch(n)

            rows = [
                self.fake_row(
                    models=models, faker=faker, type_defaults=type_defaults, pfk_combo=combo
                )
                for combo in combos_to_use
            ]

        else:
            rows = [
                self.fake_row(models=models, faker=faker, type_defaults=type_defaults)
                for _ in range(n)
            ]

        return rows
