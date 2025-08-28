import enum
import inspect
import logging
import random
from collections import deque, namedtuple
from collections.abc import Hashable
from itertools import islice, product
from pprint import pformat
from random import shuffle
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Self,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
)

from faker import Faker
from sqlalchemy import UUID, Boolean, Column, DateTime, Float, Integer, String, Text, insert
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.types import TypeEngine

logging.basicConfig(  # root logger configuration
    level=logging.INFO,  # Enable DEBUG for detailed tracing
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


PK = TypeVar("PK", bound=Hashable)

Primary_Key = namedtuple
Primary_Key_names = List[str]
UniqueValues = Dict[str, Set[Hashable]]


SeededColumnContext = Dict[str, Any]

SeedPlan = Dict[DeclarativeBase, int]


class ColumnReference:
    def __init__(self, colname: str, transform: Optional[Callable[[Any], Any]] = None):
        self.colname = colname
        self.transform = transform

    def map(self, column_context: SeededColumnContext) -> Any:
        """Return the value of the column from column_context."""
        if self.colname not in column_context:
            raise ValueError(f"Column '{self.colname}' not found in column_context")

        value = column_context[self.colname]

        if self.transform is not None:
            value = self.transform(value)

        return value

    def __repr__(self) -> str:
        tf = f", transform={self.transform}" if self.transform else ""
        return f"ColumnReference('{self.colname}'{tf})"


# Base arg type that Faker providers accept
FakerPrimitiveArg = str | int | float | bool | None

# You often want to support lists, tuples, dicts of primitives (Faker does this)
FakerComplexArg = (
    FakerPrimitiveArg | Sequence[FakerPrimitiveArg] | Mapping[str, FakerPrimitiveArg] | enum.Enum
)

FakerArg = ColumnReference | FakerComplexArg
FakerArgs = Tuple[FakerArg, ...]
FakerKwargs = Dict[str, FakerArg]


class Seed:
    def __init__(
        self,
        faker_provider: str,
        faker_args: FakerArgs = (),
        faker_kwargs: FakerKwargs = None,
    ):
        if faker_kwargs is None:
            faker_kwargs = {}
        self.provider = faker_provider
        self.dependencies: Set[str] = set()  # Track ColumnReference column names
        self.faker_args = faker_args
        self.faker_kwargs = faker_kwargs

        # Collect dependencies from ColumnReference instances in args and kwargs
        for arg in faker_args:
            if isinstance(arg, ColumnReference):
                self.dependencies.add(arg.colname)

        for value in self.faker_kwargs.values():
            if isinstance(value, ColumnReference):
                self.dependencies.add(value.colname)

        if not faker_provider:
            raise ValueError("Seed must have a faker_provider")

    def has_dependencies(self) -> bool:
        return bool(self.dependencies)

    @staticmethod
    def _generate_unique(
        # self,
        faker_function: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[Any, Any],
        used_values: Set[Any],
        max_attempts: int = 100,
    ) -> Any:
        for _ in range(max_attempts):
            value = faker_function(*args, **kwargs)
            if value not in used_values:
                return value
        print(faker_function)
        print("________________________________")
        raise RuntimeError(f"Could not generate unique value after {max_attempts} attempts")

    def generate(
        self,
        faker: Faker,
        column_context: SeededColumnContext | None = None,
        used_unique_values: Set[Any] | None = None,
    ) -> Any:
        # Validate that faker_provider exists
        if not hasattr(faker, self.provider):
            raise ValueError(f"Faker has no provider '{self.provider}'")

        faker_function = getattr(faker, self.provider)
        args, kwargs = self._resolve_args(column_context)

        sig = inspect.signature(faker_function)
        try:
            sig.bind(*args, **kwargs)
        except TypeError as e:
            print(faker_function)

            raise f"Invalid arguments. Expected signature: {sig}, got args={args}, \
            kwargs={kwargs}. Error: {e}" from e

        if used_unique_values is not None:
            return self._generate_unique(faker_function, args, kwargs, used_unique_values)
        else:
            return faker_function(*args, **kwargs)

    def _resolve_args(
        self, column_context: SeededColumnContext | None
    ) -> Tuple[FakerArgs, FakerKwargs]:
        """Resolve faker arguments and keyword arguments based on column context."""
        if not self.has_dependencies():
            return self.faker_args, self.faker_kwargs

        if column_context is None:
            raise ValueError("column_context must be provided when dependencies are present")

        for colname in self.dependencies:
            if colname not in column_context:
                raise ValueError(
                    f"Dependency column '{colname}'] \
                    from ColumnReference not found in column_context"
                )

        resolved_args = [
            arg.map(column_context) if isinstance(arg, ColumnReference) else arg
            for arg in self.faker_args
        ]

        resolved_kwargs = {
            k: v.map(column_context) if isinstance(v, ColumnReference) else v
            for k, v in self.faker_kwargs.items()
        }

        return resolved_args, resolved_kwargs

    def __repr__(self) -> str:
        dep_str = f", dependencies={self.dependencies}" if self.dependencies else ""
        return f"Seed(provider={self.provider}{dep_str})"


TypeDefaults = Dict[TypeEngine[Any], str | Seed]

TYPE_DEFAULTS: TypeDefaults = {
    Integer: Seed(faker_provider="random_int", faker_kwargs={"min": 0, "max": 1000000}),
    String: "word",
    Boolean: "boolean",
    DateTime: "date_time_this_year",
    Text: "text",
    Float: Seed(
        faker_provider="pyfloat",
        faker_kwargs={"min_value": 0.0, "max_value": 1000000.00, "right_digits": 3},
    ),
    UUID: "uuid4",
}


PK = TypeVar("PK", bound="Hashable")
Primary_Key_names = Iterable[str]


class PrimaryKeys(Generic[PK]):
    def __init__(self, pk_names: Primary_Key_names) -> None:
        if not pk_names:
            raise ValueError("Primary key names cannot be empty")
        pk_names = tuple(pk_names)  # Ensure immutable
        if len(set(pk_names)) != len(pk_names):
            raise ValueError("Primary key names must be unique")
        self._names = pk_names
        self._pks: Set["PrimaryKeys._pk_type"] = set()
        self._pk_type = namedtuple("PrimaryPK", pk_names)

    def _to_tuple(self, pk: Iterable[PK]) -> "PrimaryKeys._pk_type":
        try:
            tpl = self._pk_type(*pk)
        except TypeError as e:
            raise ValueError(f"Expected {len(self._names)} fields, got {len(pk)}") from e
        if not all(isinstance(x, Hashable) for x in tpl):
            raise TypeError(f"All components must be hashable: {tpl}")
        return tpl

    def add(self, pk: Iterable[PK]) -> None:
        tpl = self._to_tuple(pk)
        if tpl in self._pks:
            raise ValueError(f"Duplicate primary key: {tpl}")
        self._pks.add(tpl)

    def __iter__(self) -> Iterator["PrimaryKeys._pk_type"]:
        return iter(self._pks)

    def dicts(self) -> Iterator[Dict[str, PK]]:
        for pk in self._pks:
            yield dict(zip(self._names, pk, strict=False))

    def get_random(self):
        """Return a random primary key from the set."""
        if not self._pks or len(self._pks) < 1:
            raise ValueError("No primary keys available")
        return random.choice(list(self._pks))

    def __len__(self) -> int:
        return len(self._pks)

    def __contains__(self, pk: Iterable[PK]) -> bool:
        try:
            return self._to_tuple(pk) in self._pks
        except (ValueError, TypeError):
            return False


class DependencyGraph:
    def __init__(self):
        self._graph: Dict[str, Set[str]] = {}

    def add(self, node: str, dependencies: Set[str] = None):
        """Add a node with its dependencies."""
        if dependencies is None:
            dependencies = set()
        if node not in self._graph:
            self._graph[node] = set()

        self._graph[node].update(dependencies)

    def topological_sort(self) -> List[str]:
        graph = self._graph

        # 1. Ensure every dependency also appears as a key
        all_nodes = set(graph)
        for deps in graph.values():
            all_nodes.update(deps)
        graph = {n: set(graph.get(n, ())) for n in all_nodes}

        # 2. Compute reverse edges & incoming-edge counts
        incoming = {n: 0 for n in all_nodes}
        reverse = {n: set() for n in all_nodes}
        for node, deps in graph.items():
            for d in deps:
                reverse[d].add(node)
                incoming[node] += 1

        # 3. Kahn’s algorithm
        queue = deque(n for n, deg in incoming.items() if deg == 0)
        order: List[str] = []

        while queue:
            n = queue.popleft()
            order.append(n)
            for m in reverse[n]:
                incoming[m] -= 1
                if incoming[m] == 0:
                    queue.append(m)

        if len(order) != len(all_nodes):
            cycles = [n for n in all_nodes if incoming[n] != 0]
            raise ValueError(f"Cycle detected in dependency graph involving nodes: {cycles}")

        return order

    def __repr__(self):
        return f"DependencyGraph({self._graph})"


class SeedLayer:
    def __init__(
        self,
        session: Session,
        seed_plan: SeedPlan,
        type_defaults: TypeDefaults = TYPE_DEFAULTS,
    ):
        if seed_plan is None:
            raise ValueError("seed_plan is missing")
        self.type_defaults: TypeDefaults = TYPE_DEFAULTS | type_defaults
        self.faker: Faker = Faker()
        self._session: Session = session
        self._model_dependency_graph: DependencyGraph = DependencyGraph()
        self._seed_plan: SeedPlan = seed_plan
        self.models: Dict[str, SeededModel] = {}

        for model_class, nb_of_rows_to_seed in seed_plan.items():
            model = SeededModel(model_class, nb_of_rows_to_seed, session, seed_plan)

            self._model_dependency_graph.add(
                model.name,
                model.foreign_key_dependencies,
            )

            if model.name in self.models.keys():
                raise ValueError("Multiple models with same name {model.name}")

            # TODO : map talbe names to model names
            self.models[model.name] = model

        self.model_seed_order = self._model_dependency_graph.topological_sort()

    def add_faker_provider(self, provider: type) -> None:
        self.faker.add_provider(provider)

    def configure_faker(self, seed: Optional[int] = None, locale: Optional[str] = None) -> None:
        """Configure the shared Faker instance.

        Args:
            seed: Seed for reproducible results (optional).
            locale: Locale for the Faker instance, e.g., 'en_US' (optional).
        """
        providers = self.faker.providers.copy()  # Save providers
        if locale is not None:
            self.faker = Faker(locale)
            for provider in providers:
                self.faker.add_provider(provider)  # Re-add providers
        if seed is not None:
            self.faker.seed_instance(seed)

    def seed(self, batch_size: int = 1000) -> None:
        """Seed all models in seed_plan dict into the DB, respecting FK dependencies.

        Args:
            batch_size (int, optional): Number of rows to insert in each batch. Defaults to 1000.
        """
        logger.info(f"Model seeding order: {[m for m in self.model_seed_order]}")
        supports_returning = self._session.bind.dialect.supports_returning
        with self._session.begin():
            for model_name in self.model_seed_order:
                model = self.models[model_name]
                count = model.nb_of_rows_to_seed
                logger.info(f"Seeding {count} rows for {model.name}")
                fake_rows = model.fake_rows(
                    count, models=self.models, faker=self.faker, type_defaults=self.type_defaults
                )
                if not fake_rows:
                    logger.warning(f"No rows generated for model {model.name}; skipping insert")
                    continue
                for i in range(0, len(fake_rows), batch_size):
                    batch = fake_rows[i : i + batch_size]
                    if supports_returning:
                        result = self._session.scalars(
                            insert(model.base_model).returning(model.base_model), batch
                        )
                        model._process_query_result(result.all(), new_data=True)
                    else:
                        self._session.execute(insert(model.base_model), batch)
                        query = self._session.query(
                            *[getattr(model.base_model, col) for col in model.primary_keys]
                        )
                        model._process_query_result(query, new_data=True)
                    self._session.flush()

    def __repr__(self):
        # Simple printout for debugging
        return pformat(
            {
                model_class.__name__: {
                    "existing_ids": len(data.existing_ids),
                    "new_ids": len(data.new_ids),
                    "unique_values": {k: len(v) for k, v in data["unique_values"].items()},
                }
                for model_class, data in self.models.items()
            }
        )


class SeededModel:
    def __init__(
        self,
        model: Type[DeclarativeBase],
        nb_of_rows_to_seed: int,
        session: Session,
        seed_plan: SeedPlan,
    ) -> None:
        self.is_link_table = False
        self.table = model.__table__
        self.base_model = model
        self.nb_of_rows_to_seed = nb_of_rows_to_seed
        self.name = model.__name__
        self.foreign_key_dependencies: Set[str] = set()
        self.columns = {col.name: col for col in self.table.columns}
        self.primary_keys = [col.name for col in self.table.primary_key.columns]
        self.unique_columns = [col.name for col in self.table.columns if col.unique]
        self.existing_ids = PrimaryKeys[PK](self.primary_keys)
        self.new_ids = PrimaryKeys[PK](self.primary_keys)

        dependency_graph = DependencyGraph()
        primary_foreign_keys = []

        for column in model.__table__.columns:
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
            pk_values = []
            for name in self.primary_keys:
                # Try getattr for model instances, then _mapping for Row objects
                value = getattr(row, name, None)
                if value is None and hasattr(row, "_mapping"):
                    value = row._mapping.get(name)
                if value is None:
                    raise ValueError(f"Missing primary key field '{name}' in row: {row}")
                pk_values.append(value)

            pk_values = tuple(pk_values)
            id_target.add(pk_values)

            # Handle unique columns
            for col_name in self.unique_columns:
                value = getattr(row, col_name, None)
                if value is None and hasattr(row, "_mapping"):
                    value = row._mapping.get(col_name)
                if value is not None:
                    self.unique_values[col_name].add(value)

    def get_fk_combinations(self, models: Dict[str, "SeededModel"], n: int) -> list[NamedTuple]:
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
                    f"Column '{col.name}' in model '{self.__name__}' has "
                    f"{len(col.foreign_keys)} foreign keys; expected exactly one."
                )
            fk = next(iter(col.foreign_keys))
            target_table = fk.column.table
            target_model = self.table_to_model(col, target_table, models)

            target_field = fk.column.name
            pk_data = models[target_model.name].new_ids  # PrimaryKeys object

            if not pk_data:
                raise ValueError(f"No new IDs for FK '{col.name}' -> '{target_table.name}'")

            ids = [getattr(pk, target_field) for pk in pk_data]
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
        FKCombination = namedtuple("FKCombination", fk_targets)
        combo_iter = (FKCombination(*combo) for combo in product(*value_lists))

        return list(islice(combo_iter, n))

    def table_to_model(
        self,
        column: Column,
        table: Any,  # Table type from SQLAlchemy, or use Table if imported
        models: Dict[str, "SeededModel"],
    ) -> "SeededModel":
        target_model: "SeededModel" = None
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
        models: Dict[str, "SeededModel"],
        faker: Faker,
        type_defaults: TypeDefaults,
        column_context: Dict[str, Any],
        pfk_combo: Any = None,  # NamedTuple or None
    ) -> Any:
        column = self.columns[col_name]

        # Skip autoincrement PKs
        if column.autoincrement is True:
            return None

        # Handle Primary keys that are also foreign keys, must use valid combination
        if column.foreign_keys and column.primary_key:
            if pfk_combo is None:
                raise (
                    f"No combination of foreign key profided for \
                    column {column} in model {self.name}"
                )

            if col_name not in pfk_combo._fields:
                raise ValueError(
                    f"Field '{col_name}' not found in primary key combination : {pfk_combo}"
                )

            # fk = next(iter(column.foreign_keys))
            # target_table = fk.column.table
            return getattr(pfk_combo, col_name)

        if column.foreign_keys:
            # For now: assume single FK per column
            fk = next(iter(column.foreign_keys))
            target_table = fk.column.table
            target_model = self.table_to_model(column, target_table, models)

            # Pick random ID from models and extract the scalar value
            pk_tuple = models[target_model.name].new_ids.get_random()
            target_field = fk.column.name  # The referenced column name (e.g., 'id')
            return getattr(pk_tuple, target_field)  # Extract the scalar value

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

        if column.default:
            return column.default.arg()

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
        models: Dict[str, Self],
        faker: Faker,
        type_defaults: TypeDefaults,
        pfk_combo: NamedTuple = None,
    ):
        column_context = {}
        row = {}

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

    def fake_rows(self, n: int, models: Dict[str, Self], faker: Faker, type_defaults: TypeDefaults):
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


class SeededColumnMixin:
    """Adds `seed` and `generate()` behaviour."""

    def __init__(
        self,
        *args,
        seed: Seed | str | None = None,
        nullable_chance: int = 20,
        **kwargs,
    ):
        # Allow    Integer   → Integer()
        if args and isinstance(args[0], type):
            args = (args[0](), *args[1:])

        if isinstance(seed, str):
            seed = Seed(faker_provider=seed)

        self.seed = seed
        self.nullable_chance = nullable_chance

        # Pass everything downstream
        super().__init__(*args, **kwargs)

    # --------------------------------------------------------------------- #
    # Data generation helper
    # --------------------------------------------------------------------- #
    def generate(
        self,
        faker: Faker,
        column_context: dict | None = None,
        used_unique_values: Set[Any] | None = None,
    ):
        if self.nullable and faker.random_int(min=1, max=100) <= self.nullable_chance:
            return None

        return self.seed.generate(
            column_context=column_context,
            faker=faker,
            used_unique_values=used_unique_values,
        )

    # Nice repr so SQLAlchemy debug‐prints stay readable
    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SeededColumn({self.name or '<unnamed>'}, "
            f"type={self.type}, nullable={self.nullable}, "
            f"pk={self.primary_key}, autoincrement={self.autoincrement}, "
            f"server_default={self.server_default})"
        )


# Custom Column class
class SeededColumn(SeededColumnMixin, Column):
    inherit_cache = True  # 🚀 enable SQL compilation caching
