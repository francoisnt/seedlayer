import random
from collections.abc import Hashable, Iterable, Iterator
from typing import Dict, Generic

from .types import PK


class PrimaryKeys(Generic[PK]):
    """Track unique primary key values for a model."""

    def __init__(self, pk_names: Iterable[str]) -> None:
        names = tuple(pk_names)
        if not names:
            raise ValueError("Primary key names cannot be empty")
        if len(set(names)) != len(names):
            raise ValueError("Primary key names must be unique")
        self._names: tuple[str, ...] = names
        self._pks: set[tuple[PK, ...]] = set()

    def _validate(self, pk: Iterable[PK]) -> tuple[PK, ...]:
        values = tuple(pk)
        expected = len(self._names)
        if len(values) != expected:
            raise ValueError(f"Expected {expected} fields, got {len(values)}")
        if not all(isinstance(value, Hashable) for value in values):
            raise TypeError(f"All components must be hashable: {values}")
        return values

    def add(self, pk: Iterable[PK]) -> None:
        values = self._validate(pk)
        if values in self._pks:
            raise ValueError(f"Duplicate primary key: {values}")
        self._pks.add(values)

    def __iter__(self) -> Iterator[tuple[PK, ...]]:
        return iter(self._pks)

    def _as_mapping(self, pk: tuple[PK, ...]) -> Dict[str, PK]:
        return dict(zip(self._names, pk, strict=True))

    def dicts(self) -> Iterator[Dict[str, PK]]:
        for pk in self._pks:
            yield self._as_mapping(pk)

    def get_random(self) -> Dict[str, PK]:
        """Return a random primary key as a mapping of column name to value."""
        if not self._pks:
            raise ValueError("No primary keys available")
        return self._as_mapping(random.choice(tuple(self._pks)))

    def __len__(self) -> int:
        return len(self._pks)

    def __contains__(self, pk: Iterable[PK]) -> bool:
        try:
            return self._validate(pk) in self._pks
        except (ValueError, TypeError):
            return False
