from collections.abc import Callable
from typing import (
    Any,
)

from .types import SeededColumnContext


class ColumnReference:
    """Represents a reference to a column with an optional transform function."""

    def __init__(self, colname: str, transform: Callable[[Any], Any] | None = None):
        """Initialize a ColumnReference.

        Args:
            colname: The name of the column to reference.
            transform: An optional function to apply to the column value.
        """
        self.colname = colname
        self.transform = transform

    def map(self, column_context: SeededColumnContext) -> Any:
        """Return the value of the column from column_context, applying the transform if set.

        Args:
            column_context: Dictionary containing column values.

        Returns:
            The column value, potentially transformed.

        Raises:
            ValueError: If the column name is not found in column_context.
        """
        if self.colname not in column_context:
            raise ValueError(f"Column '{self.colname}' not found in column_context")

        value = column_context[self.colname]

        if self.transform is not None:
            value = self.transform(value)

        return value

    def __repr__(self) -> str:
        """Return a string representation of the ColumnReference."""
        tf = f", transform={self.transform}" if self.transform else ""
        return f"ColumnReference('{self.colname}'{tf})"
