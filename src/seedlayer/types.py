from collections import namedtuple
from collections.abc import Hashable
from typing import Any, Dict, Set, Tuple, TypeVar

from sqlalchemy.orm import DeclarativeBase

SeededColumnContext = Dict[str, Any]

SeedPlan = Dict[DeclarativeBase, int]

PK = TypeVar("PK", bound=Hashable)
Primary_Key = namedtuple
Primary_Key_names = Tuple[str]
UniqueValues = Dict[str, Set[Hashable]]
