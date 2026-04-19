"""Output formatting mixin for CLI contexts."""

import json
import traceback
from typing import Any

import yaml
from rich.syntax import Syntax

from pyclif.core.output import ExceptionTable, Response


class _FallbackEncoder(json.JSONEncoder):
    """JSON encoder that degrades gracefully for non-serializable objects.

    Resolution order for each value that the default encoder cannot handle:
    1. `to_dict()` — pyclif / domain objects that expose a serialization method.
    2. `__dict__` — generic Python instances.
    3. `str()` — last resort; preserves readability without crashing.
    """

    def default(self, obj: Any) -> Any:
        """Encode non-serializable objects using available introspection methods."""
        if callable(getattr(obj, "to_dict", None)):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)


class OutputFormatMixin:
    """Provide methods for printing error messages and results based on a specified format.

    This mixin expects the inheriting class to have 'console' and 'output_format' attributes.
    """

    def print_error_based_on_format(self, exception: Exception) -> None:
        """Print the error message based on the specified format.

        Args:
            exception (Exception): The exception to be printed.
        """
        message = {
            "success": False,
            "error_code": type(exception).__name__,
            "message": str(exception),
            "data": traceback.format_exc(),
        }
        if getattr(self, "output_format", None) == "table":
            self.print_result_based_on_format(message, options={"callback": ExceptionTable})
        else:
            self.print_result_based_on_format(message)

    def print_result_based_on_format(self, result: Any, options: dict | None = None) -> None:
        """Print the result based on the specified format.

        Args:
            result: The result to be printed.
            options: Additional options — callback, filter_value, default_filter_value.
        """
        if options is None:
            options = {}
        dispatch = {
            "json": self._print_json,
            "yaml": self._print_yaml,
            "table": self._print_table,
            "rich": self._print_rich,
            "raw": self._print_raw,
        }
        output_format = getattr(self, "output_format", None)
        print_func = dispatch.get(output_format, self._print_raw)  # type: ignore
        # noinspection PyArgumentList
        print_func(result, options)

    def _print_json(self, result: Any, options: dict) -> None:
        """Print the result as JSON, serializing a Response if needed.

        Uses _FallbackEncoder so that domain objects not handled by
        Response._serialize_data() (no to_dict(), non-standard types) are
        still rendered rather than raising a TypeError.
        """
        if isinstance(result, Response):
            result = result.to_json()
        # Filter out options aren't supported by print_json
        clean_options = {
            k: v
            for k, v in options.items()
            if k not in ["callback", "filter_value", "default_filter_value"]
        }
        json_str = json.dumps(result, cls=_FallbackEncoder)
        self.console.print_json(json_str, **clean_options)  # type: ignore

    def _print_yaml(self, result: Any, options: dict) -> None:
        """Print the result as syntax-highlighted YAML, serializing a Response if needed."""
        if isinstance(result, Response):
            result = result.to_json()
        yaml_content = yaml.dump(result, allow_unicode=True, indent=2, sort_keys=False)
        clean_options = {
            k: v
            for k, v in options.items()
            if k not in ["callback", "filter_value", "default_filter_value"]
        }
        self.console.print(  # type: ignore
            Syntax(yaml_content, "yaml", theme="ansi_dark"), soft_wrap=True, **clean_options
        )

    def _print_table(self, result: Any, options: dict) -> None:
        """Print the result as a table using a Response callback or a direct callback."""
        if isinstance(result, Response):
            self.console.print(result.to_table())  # type: ignore
            return

        callback = options.get("callback")
        if callback is not None:
            self.console.print(callback(result))  # type: ignore
        else:
            self.console.print(result)  # type: ignore

    def _print_rich(self, result: Any, options: dict) -> None:
        """Print the result using rich rendering via a Response callback or a direct callback."""
        if isinstance(result, Response):
            self.console.print(result.to_rich())  # type: ignore
            return

        callback = options.get("callback")
        if callback is not None:
            self.console.print(callback(result))  # type: ignore
        else:
            self.console.print(result)  # type: ignore

    def _print_raw(self, result: Any, options: dict) -> None:
        """Print the result as plain text, optionally filtering a single key from the data."""
        if isinstance(result, Response):
            result = result.to_json()

        filter_key = options.get("filter_value")
        default_value = options.get("default_filter_value")

        if filter_key and isinstance(result, dict):
            # Look inside `data` first (the structured payload), then fall back
            # to the top-level response fields (success, message, error_code…).
            data = result.get("data")
            if isinstance(data, dict) and filter_key in data:
                self.console.print(data.get(filter_key, default_value))  # type: ignore
            else:
                self.console.print(result.get(filter_key, default_value))  # type: ignore
        else:
            self.console.print(result)  # type: ignore
