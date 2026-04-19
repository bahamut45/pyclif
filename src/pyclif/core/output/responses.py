"""Response class"""

import dataclasses
from collections.abc import Callable
from operator import attrgetter
from typing import Any

NON_SERIALIZABLE_FIELDS = ["callback_table_output", "callback_rich_output"]


@dataclasses.dataclass
class Response:
    """Represents a CLI command response with structured output support.

    Attributes:
        success: Indicates whether the response is successful.
        message: The message associated with the response.
        data: Additional data associated with the response.
        error_code: The error code associated with the response.
        callback_table_output: Callback function for generating table output.
        callback_rich_output: Callback function for generating rich output.
    """

    success: bool
    message: str
    data: Any = dataclasses.field(default_factory=dict)
    error_code: int | None = None
    callback_table_output: Callable | None = None
    callback_rich_output: Callable | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the object.

        Only includes fields whose values differ from their defaults.

        Returns:
            Dictionary mapping attribute names to their values.
        """
        return dict(
            (f.name, attrgetter(f.name)(self))
            for f in dataclasses.fields(self)
            if attrgetter(f.name)(self) != f.default
        )

    def to_json(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary of the response.

        Non-serializable fields (callbacks) are excluded from the output.

        Returns:
            Dictionary containing the serializable attributes.
        """
        self._serialize_data()
        data = self.to_dict()
        for field in NON_SERIALIZABLE_FIELDS:
            data.pop(field, None)
        return data

    def to_table(self) -> str:
        """Convert the response to a table format using the registered callback.

        Returns:
            The table representation of the response.

        Raises:
            RuntimeError: If no table output callback is registered.
        """
        if self.callback_table_output is not None:
            return self.callback_table_output(self)
        else:
            raise RuntimeError("No Callback to generate table output available")

    def to_rich(self) -> str:
        """Convert the response to a rich format using the registered callback.

        Returns:
            The rich representation of the response.

        Raises:
            RuntimeError: If no rich output callback is registered.
        """
        if self.callback_rich_output is not None:
            return self.callback_rich_output(self)
        else:
            raise RuntimeError("No Callback to generate rich output available")

    def _serialize_data(self):
        """Serialize dict values that expose a to_dict method in place."""
        if isinstance(self.data, dict):
            serialized_dict = {}
            for key, value in self.data.items():
                if (hasattr(value, "to_dict")) and callable(value.to_dict):
                    serialized_dict[key] = value.to_dict()
                else:
                    serialized_dict[key] = value
            self.data = serialized_dict
