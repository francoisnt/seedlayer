"""Type definitions for seedlayer."""

from collections.abc import Hashable, Mapping
from typing import Any, TypeVar

SeededColumnContext = dict[str, Any]

SeedingPlan = Mapping[type[Any], int]

PK = TypeVar("PK", bound=Hashable)
Primary_Key_names = tuple[str, ...]
UniqueValues = dict[str, set[Hashable]]
