from collections.abc import Hashable
from typing import Any, Dict, Mapping, Set, TypeVar

SeededColumnContext = Dict[str, Any]

SeedPlan = Mapping[type[Any], int]

PK = TypeVar("PK", bound=Hashable)
Primary_Key_names = tuple[str, ...]
UniqueValues = Dict[str, Set[Hashable]]
