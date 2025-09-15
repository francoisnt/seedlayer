from collections import namedtuple
from collections.abc import Hashable
from typing import Any, Dict, List, Set, TypeVar

from sqlalchemy.orm import DeclarativeBase

SeededColumnContext = Dict[str, Any]

SeedPlan = Dict[DeclarativeBase, int]

PK = TypeVar("PK", bound=Hashable)
Primary_Key = namedtuple
Primary_Key_names = List[str]
UniqueValues = Dict[str, Set[Hashable]]
