from typing import Any, TYPE_CHECKING, Set

from faker import Faker
from sqlalchemy import Column
from sqlalchemy.sql.type_api import TypeEngine

from .seed import Seed
from .types import SeededColumnContext

if TYPE_CHECKING:
    from sqlalchemy import Column as SQLAlchemyColumn
    ColumnBase = SQLAlchemyColumn[Any]
else:  # pragma: no cover - runtime behaviour only
    ColumnBase = Column


class SeededColumnMixin:
    """Adds `seed` and `generate()` behaviour."""

    seed: Seed | None
    nullable: bool | None
    name: str
    type: TypeEngine[Any]
    primary_key: bool
    autoincrement: Any
    server_default: Any

    def __init__(
        self,
        *args: Any,
        seed: Seed | str | None = None,
        nullable_chance: int = 20,
        **kwargs: Any,
    ) -> None:
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
        column_context: SeededColumnContext | None = None,
        used_unique_values: Set[Any] | None = None,
    ) -> Any | None:
        if self.nullable and faker.random_int(min=1, max=100) <= self.nullable_chance:
            return None

        if self.seed is None:
            raise ValueError("SeededColumn requires a Seed to generate values")

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
class SeededColumn(SeededColumnMixin, ColumnBase):
    inherit_cache = True  # 🚀 enable SQL compilation caching
