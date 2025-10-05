import enum
import inspect
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from faker import Faker

from .column_reference import ColumnReference
from .types import SeededColumnContext

# Base arg type that Faker providers accept
FakerPrimitiveArg = str | int | float | bool | None

# You often want to support lists, tuples, dicts of primitives (Faker does this)
FakerComplexArg = (
    FakerPrimitiveArg | Sequence[FakerPrimitiveArg] | Mapping[str, FakerPrimitiveArg] | enum.Enum
)

FakerArg = ColumnReference | FakerComplexArg
FakerArgs = tuple[FakerArg, ...]
FakerKwargs = dict[str, FakerArg]


class Seed:
    """Represents a seed configuration for generating fake data using Faker."""

    def __init__(
        self,
        faker_provider: str,
        faker_args: FakerArgs = (),
        faker_kwargs: FakerKwargs | None = None,
    ) -> None:
        """Initialize a Seed with faker provider and arguments.

        Args:
            faker_provider: The name of the Faker provider method.
            faker_args: Arguments to pass to the Faker provider.
            faker_kwargs: Keyword arguments to pass to the Faker provider.
        """
        if faker_kwargs is None:
            faker_kwargs = {}
        self.provider = faker_provider
        self.dependencies: set[str] = set()  # Track ColumnReference column names
        self.faker_args = faker_args
        self.faker_kwargs: FakerKwargs = faker_kwargs

        # Collect dependencies from ColumnReference instances in args and kwargs
        for arg in faker_args:
            if isinstance(arg, ColumnReference):
                self.dependencies.add(arg.colname)

        for value in self.faker_kwargs.values():
            if isinstance(value, ColumnReference):
                self.dependencies.add(value.colname)

        if not faker_provider:
            raise ValueError("Seed must have a faker_provider")

    def has_dependencies(self) -> bool:
        return bool(self.dependencies)

    @staticmethod
    def _generate_unique(
        # self,
        faker_function: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[Any, Any],
        used_values: set[Any],
        max_attempts: int = 100,
    ) -> Any:
        for _ in range(max_attempts):
            value = faker_function(*args, **kwargs)
            if value not in used_values:
                return value
        raise RuntimeError(f"Could not generate unique value after {max_attempts} attempts")

    def generate(
        self,
        faker: Faker,
        column_context: SeededColumnContext | None = None,
        used_unique_values: set[Any] | None = None,
    ) -> Any:
        # Validate that faker_provider exists
        if not hasattr(faker, self.provider):
            raise ValueError(f"Faker has no provider '{self.provider}'")

        faker_function = getattr(faker, self.provider)
        args, kwargs = self._resolve_args(column_context)

        sig = inspect.signature(faker_function)
        try:
            sig.bind(*args, **kwargs)
        except TypeError as e:
            raise TypeError(
                f"Invalid arguments. Expected signature: {sig}; got args={args}, kwargs={kwargs}."
            ) from e
        if used_unique_values is not None:
            return self._generate_unique(faker_function, args, kwargs, used_unique_values)
        else:
            return faker_function(*args, **kwargs)

    def _resolve_args(
        self, column_context: SeededColumnContext | None
    ) -> tuple[FakerArgs, FakerKwargs]:
        """Resolve faker arguments and keyword arguments based on column context."""
        if not self.has_dependencies():
            return self.faker_args, self.faker_kwargs

        if column_context is None:
            raise ValueError("column_context must be provided when dependencies are present")

        for colname in self.dependencies:
            if colname not in column_context:
                raise ValueError(
                    f"Dependency column '{colname}'] \
                    from ColumnReference not found in column_context"
                )

        resolved_args = [
            arg.map(column_context) if isinstance(arg, ColumnReference) else arg
            for arg in self.faker_args
        ]

        resolved_kwargs = {
            k: v.map(column_context) if isinstance(v, ColumnReference) else v
            for k, v in self.faker_kwargs.items()
        }

        return tuple(resolved_args), resolved_kwargs

    def __repr__(self) -> str:
        dep_str = f", dependencies={self.dependencies}" if self.dependencies else ""
        return f"Seed(provider={self.provider}{dep_str})"
