from typing import (
    Any,
    Set,
)

from faker import Faker
from sqlalchemy import Column

from .seed import Seed


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
