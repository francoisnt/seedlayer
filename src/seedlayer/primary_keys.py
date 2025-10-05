import random
from collections.abc import Hashable, Iterable, Iterator
from typing import Generic

from .types import PK


class PrimaryKeys(Generic[PK]):
    """Track unique primary key values for a model."""

    def __init__(self, pk_names: Iterable[str]) -> None:
        """Initialize PrimaryKeys with primary key column names.

        Args:
            pk_names: An iterable of primary key column names.

        Raises:
            ValueError: If no primary key names are provided or if names are not unique.
        """
        names = tuple(pk_names)
        if not names:
            raise ValueError("Primary key names cannot be empty")
        if len(set(names)) != len(names):
            raise ValueError("Primary key names must be unique")
        self._names: tuple[str, ...] = names
        self._pks: set[tuple[PK, ...]] = set()

    def _validate(self, pk: Iterable[PK]) -> tuple[PK, ...]:
        """Validate a primary key tuple for length and hashability.

        Args:
            pk: The primary key components.

        Returns:
            The primary key as a tuple.

        Raises:
            ValueError: If the number of components does not match the number of primary key names.
            TypeError: If any component is not hashable.
        """
        values = tuple(pk)
        expected = len(self._names)
        if len(values) != expected:
            raise ValueError(f"Expected {expected} fields, got {len(values)}")
        if not all(isinstance(value, Hashable) for value in values):
            raise TypeError(f"All components must be hashable: {values}")
        return values

    def add(self, pk: Iterable[PK]) -> None:
        """Add a primary key to the set.

        Args:
            pk: The primary key components to add.

        Raises:
            ValueError: If the primary key is a duplicate.
        """
        values = self._validate(pk)
        if values in self._pks:
            raise ValueError(f"Duplicate primary key: {values}")
        self._pks.add(values)

    def __iter__(self) -> Iterator[tuple[PK, ...]]:
        """Iterate over the primary key tuples."""
        return iter(self._pks)

    def _as_mapping(self, pk: tuple[PK, ...]) -> dict[str, PK]:
        """Convert a primary key tuple to a dictionary mapping column names to values.

        Args:
            pk: The primary key tuple.

        Returns:
            A dictionary with column names as keys and primary key values as values.
        """
        return dict(zip(self._names, pk, strict=True))

    def dicts(self) -> Iterator[dict[str, PK]]:
        """Yield dictionaries mapping column names to values for each primary key."""
        for pk in self._pks:
            yield self._as_mapping(pk)

    def get_random(self) -> dict[str, PK]:
        """Return a random primary key as a mapping of column name to value."""
        if not self._pks:
            raise ValueError("No primary keys available")
        return self._as_mapping(random.choice(tuple(self._pks)))  # noqa: S311

    def __len__(self) -> int:
        """Return the number of primary keys stored."""
        return len(self._pks)

    def __contains__(self, pk: Iterable[PK]) -> bool:
        """Check if the given primary key components are contained in the set.

        Args:
            pk: The primary key components to check.

        Returns:
            True if the primary key is contained, False otherwise.
        """
        try:
            return self._validate(pk) in self._pks
        except (ValueError, TypeError):
            return False
