from typing import Any

from sqlalchemy import UUID, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.types import TypeEngine

from .seed import Seed

TypeDefaults = dict[type[TypeEngine[Any]], str | Seed]

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
