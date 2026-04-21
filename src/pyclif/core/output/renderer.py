"""Renderer protocol and base class for all pyclif output formats."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from rich.console import Console
from rich.panel import Panel

if TYPE_CHECKING:
    from .responses import OperationResult, Response
    from .tables import CliTable, CliTableColumn


class ResponseRenderer(Protocol):
    """Protocol for renderer implementations.

    Renderers are the single source of truth for all output formats of a command.
    Implement this Protocol directly only when inheriting BaseRenderer is not
    appropriate. All methods called by the framework must be present.
    """

    def serialize(self, response: Response) -> dict:
        """Return a JSON-serializable dict for the response."""
        ...

    def table(self, response: Response) -> CliTable:
        """Build a CliTable from the response results."""
        ...

    def raw(self, response: Response) -> str:
        """Return a plain-text representation of the response."""
        ...

    def rich(self, response: Response, console: Console) -> None:
        """Print a static Rich display (panels, markdown, tables) to console."""
        ...

    def rich_setup(self) -> Any:
        """Return the initial Rich renderable for the Live context."""
        ...

    def rich_on_item(self, result: OperationResult, all_so_far: list) -> None:
        """Update the Live renderable after each streamed item."""
        ...

    def rich_summary(self, response: Response, console: Console) -> None:
        """Print a summary after the Live context closes."""
        ...

    def get_success_message(self, results: list) -> str:
        """Return the success message for a completed batch."""
        ...

    def get_failure_message(self, results: list) -> str:
        """Return the failure message for a partially or fully failed batch."""
        ...


class BaseRenderer:
    """Declarative base class for pyclif output renderers.

    Subclass and declare class attributes to control every output format.
    Override individual hooks for custom behaviour. Override the full method
    only as a last resort.

    Class attributes:
        fields: Field names included in JSON/YAML serialization. Empty means
            all fields via the standard Response.to_json() fallback.
        columns: Column names for table output. Falls back to fields when empty.
        rich_title: Panel title used by the default rich() and table() display.
        success_message: Static success message returned by get_success_message().
        failure_message: Static failure message returned by get_failure_message().

    Implementation note — class-level lists: fields and columns are ClassVar.
    Subclasses override them as plain class attributes (never mutated at runtime).
    get_fields() and get_columns() always return a copy so callers cannot
    accidentally mutate the class-level list.
    """

    fields: ClassVar[list[str]] = []
    columns: ClassVar[list[str]] = []
    rich_title: ClassVar[str] = ""
    success_message: ClassVar[str] = ""
    failure_message: ClassVar[str] = ""

    def get_fields(self) -> list[str]:
        """Return a copy of the declared fields list."""
        return list(self.fields)

    def get_columns(self) -> list[str]:
        """Return a copy of the declared columns list, falling back to fields."""
        return list(self.columns) or list(self.fields)

    def _result_to_row(self, result: OperationResult, columns: list[str]) -> dict:
        """Extract a row dict from an OperationResult for the given column names.

        Checks result.data first (domain payload), then falls back to top-level
        OperationResult attributes (item, success, message, error_code).

        Args:
            result: The operation result to extract data from.
            columns: Column names to extract.

        Returns:
            Dict mapping each column name to its value.
        """
        row = {}
        for col in columns:
            if isinstance(result.data, dict) and col in result.data:
                row[col] = result.data[col]
            else:
                row[col] = getattr(result, col, None)
        return row

    def serialize(self, response: Response) -> dict:
        """Return a JSON-serializable dict filtered to self.fields.

        When fields is empty, delegates to response.to_json() for full
        serialization with standard exclusions.

        Args:
            response: The command response to serialize.

        Returns:
            Dict suitable for JSON/YAML output.
        """
        fields = self.get_fields()
        if not fields:
            return response.to_json()

        results = response.data.get("results", [])
        serialized = [
            {
                f: (r.data.get(f) if isinstance(r.data, dict) else None)
                if isinstance(r.data, dict) and f in r.data
                else getattr(r, f, None)
                for f in fields
            }
            for r in results
        ]
        return {
            "success": response.success,
            "message": response.message,
            "error_code": response.error_code,
            "data": {"results": serialized},
        }

    def table(self, response: Response) -> CliTable:
        """Build a CliTable from response.data["results"] using self.columns.

        Args:
            response: The command response carrying the results list.

        Returns:
            A CliTable instance ready for console.print().
        """
        # Lazy import — renderer.py and tables.py are in the same package;
        # importing at module level would create a circular dependency via
        # responses.py (which imports BaseRenderer for its renderer field).
        from .tables import CliTable, CliTableColumn  # noqa: PLC0415

        cols = self.get_columns()
        fields_dict: dict[str, CliTableColumn] = {
            col: CliTableColumn(header=col.replace("_", " ").title()) for col in cols
        }
        results = response.data.get("results", [])
        rows = [self._result_to_row(r, cols) for r in results]
        title = self.rich_title or response.message or None
        return CliTable(
            fields=fields_dict,
            rows=rows,
            table_style={"title": title} if title else None,
        )

    # noinspection PyMethodMayBeStatic
    def raw(self, response: Response) -> str:
        """Return the response message as plain text.

        Args:
            response: The command response.

        Returns:
            The response message string.
        """
        return response.message

    def rich(self, response: Response, console: Console) -> None:
        """Display a panel with the response message.

        Override for panels, rules, markdown, or any static Rich display.

        Args:
            response: The command response to display.
            console: The Rich console to print to.
        """
        title = self.rich_title or None
        console.print(Panel(response.message, title=title))

    def rich_setup(self) -> Any:
        """Return the initial renderable for the Live context.

        Called once before iteration starts. Override to create and store
        stateful Rich objects (Progress, Layout, etc.) as instance attributes
        so rich_on_item() can mutate them.

        Returns:
            A Rich renderable to wrap in Live().
        """
        return Panel("Working…")

    def rich_on_item(self, result: OperationResult, all_so_far: list) -> None:
        """Called after each streamed item inside the Live context.

        Override to mutate the Rich objects created in rich_setup().

        Args:
            result: The latest OperationResult.
            all_so_far: All results received so far, including result.
        """

    def rich_summary(self, response: Response, console: Console) -> None:
        """Called after all items are processed and the Live context is closed.

        Defaults to the static rich() display. Override for a custom summary.

        Args:
            response: The fully materialised response with all results.
            console: The Rich console to print to.
        """
        self.rich(response, console)

    def get_success_message(self, results: list) -> str:
        """Return the success message for a completed batch.

        Args:
            results: All OperationResult items from the batch.

        Returns:
            Human-readable success message.
        """
        return self.success_message or f"{len(results)} operation(s) completed successfully."

    def get_failure_message(self, results: list) -> str:
        """Return the failure message for a partially or fully failed batch.

        Args:
            results: All OperationResult items from the batch.

        Returns:
            Human-readable failure message with failure count.
        """
        if self.failure_message:
            return self.failure_message
        failed = sum(1 for r in results if not r.success)
        return f"{failed}/{len(results)} operation(s) failed."
