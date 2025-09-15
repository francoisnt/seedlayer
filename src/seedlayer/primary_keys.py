import random
from collections import namedtuple
from collections.abc import Hashable
from typing import (
    Dict,
    Generic,
    Iterable,
    Iterator,
    Set,
)

from .types import PK, Primary_Key_names


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
