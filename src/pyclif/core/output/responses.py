"""Response and OperationResult classes."""

from __future__ import annotations

import dataclasses
import warnings
from collections.abc import Callable, Iterator
from operator import attrgetter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .renderer import BaseRenderer

NON_SERIALIZABLE_FIELDS = ["callback_table_output", "callback_rich_output", "renderer"]


@dataclasses.dataclass
class OperationResult:
    """Outcome of a single interface action.

    Interface methods return this instead of rising for expected business
    failures. Exceptions are reserved for programming errors (broken invariant,
    missing template, corrupt state).

    Attributes:
        success: Whether the action succeeded.
        item: Human-readable identifier (file path, resource name, …).
        data: Optional payload attached to the result.
        message: Human-readable description of the outcome.
        error_code: Non-zero on failure.
    """

    success: bool
    item: str
    data: Any = None
    message: str = ""
    error_code: int = 0

    @classmethod
    def ok(cls, item: str, message: str = "", data: Any = None) -> OperationResult:
        """Create a successful result.

        Args:
            item: Human-readable identifier for the operated resource.
            message: Human-readable description of what happened.
            data: Optional domain payload.

        Returns:
            A successful OperationResult with error_code 0.
        """
        return cls(success=True, item=item, message=message, data=data)

    @classmethod
    def error(cls, item: str, message: str, error_code: int = 1) -> OperationResult:
        """Create a failed result.

        Args:
            item: Human-readable identifier for the operated resource.
            message: Description of the failure.
            error_code: Exit code for this failure (default 1).

        Returns:
            A failed OperationResult with the given error_code.
        """
        return cls(success=False, item=item, message=message, error_code=error_code)


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
    renderer: BaseRenderer | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the object.

        Only includes fields whose values differ from their defaults.

        Returns:
            Dictionary mapping attributes names to their values.
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
        warnings.warn(
            "callback_table_output / to_table() is deprecated. "
            "Use a BaseRenderer subclass instead.",
            DeprecationWarning,
            stacklevel=2,
        )
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
        warnings.warn(
            "callback_rich_output / to_rich() is deprecated. Use a BaseRenderer subclass instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.callback_rich_output is not None:
            return self.callback_rich_output(self)
        else:
            raise RuntimeError("No Callback to generate rich output available")

    @classmethod
    def from_results(
        cls,
        results: list[OperationResult],
        message: str = "",
        success_message: str = "",
        failure_message: str = "",
        table: type | None = None,
        renderer: BaseRenderer | None = None,
    ) -> Response:
        """Build a Response from a list of OperationResult.

        Aggregates a batch of interface results into a single Response.
        success is True only if every result succeeded. error_code is taken
        from the first failed result, or 0 if all passed.

        Args:
            results: Outcomes returned by the interface layer.
            message: Fixed message used regardless of the outcome. When omitted,
                success_message / failure_message are used, or a default
                summary is generated from the result counts.
            success_message: Message used when all results succeeded.
            failure_message: Message used when at least one result failed.
            table: Deprecated. Table callback class (kept for backward compatibility).
            renderer: Renderer instance controlling all output formats.

        Returns:
            An aggregated Response reflecting the overall outcome.
        """
        if table is not None:
            warnings.warn(
                "The 'table' parameter of from_results() is deprecated. "
                "Pass a BaseRenderer instance via 'renderer' instead.",
                DeprecationWarning,
                stacklevel=2,
            )

        failed = [r for r in results if not r.success]
        success = not failed
        error_code = failed[0].error_code if failed else 0

        if not message:
            if success:
                message = success_message or f"{len(results)} operation(s) completed successfully."
            else:
                message = failure_message or f"{len(failed)}/{len(results)} operation(s) failed."

        return cls(
            success=success,
            message=message,
            data={"results": results},
            error_code=error_code if not success else None,
            callback_table_output=table,
            renderer=renderer,
        )

    @classmethod
    def from_stream(
        cls,
        stream: Iterator[OperationResult],
        renderer: BaseRenderer,
    ) -> Response:
        """Build a Response from a generator of OperationResult.

        The generator is stored without being consumed. The framework
        materialises it at dispatch time: for rich output the Live context
        drives iteration via renderer hooks; for all other formats
        OutputFormatMixin calls _materialise_stream() before dispatch.

        success, message, and error_code are left blank — they are
        re-evaluated by the framework after the stream is consumed, using
        renderer.get_success_message() / get_failure_message().

        Args:
            stream: Generator yielding OperationResult items one by one.
            renderer: Renderer instance — required, a stream with no renderer
                has no output contract.

        Returns:
            An incomplete Response carrying the stream and renderer.
        """
        return cls(
            success=True,
            message="",
            data={"stream": stream},
            renderer=renderer,
        )

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
