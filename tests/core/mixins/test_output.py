"""Unit tests for the OutputFormatMixin."""

from unittest.mock import MagicMock, patch

from pyclif.core.mixins.output import OutputFormatMixin
from pyclif.core.output import ExceptionTable, Response


class DummyOutputContext(OutputFormatMixin):
    """Dummy context class to test the OutputFormatMixin.

    Provides the required 'console' and 'output_format' attributes.
    """

    def __init__(self, output_format: str = "raw") -> None:
        """Initialize the dummy context with a mocked console and specific format.

        Args:
            output_format (str): The mock output format (e.g., 'json', 'table').
        """
        self.console = MagicMock()
        self.output_format = output_format


class TestOutputFormatMixin:
    """Test suite for the OutputFormatMixin class."""

    def test_print_error_based_on_format_default(self) -> None:
        """Test error printing when the format is not 'table'."""
        context = DummyOutputContext(output_format="json")
        context.print_result_based_on_format = MagicMock()  # type: ignore

        try:
            raise ValueError("Something went wrong")
        except ValueError as exception:
            context.print_error_based_on_format(exception)

        context.print_result_based_on_format.assert_called_once()

        call_args = context.print_result_based_on_format.call_args[0][0]
        assert call_args["success"] is False
        assert call_args["error_code"] == "ValueError"
        assert call_args["message"] == "Something went wrong"
        assert "Traceback" in call_args["data"]

    def test_print_error_based_on_format_table(self) -> None:
        """Test error printing routes to ExceptionTable when a format is 'table'."""
        context = DummyOutputContext(output_format="table")
        context.print_result_based_on_format = MagicMock()  # type: ignore

        try:
            raise RuntimeError("Table error")
        except RuntimeError as exception:
            context.print_error_based_on_format(exception)

        context.print_result_based_on_format.assert_called_once()
        call_options = context.print_result_based_on_format.call_args[1].get("options", {})
        assert call_options.get("callback") == ExceptionTable

    def test_print_result_dispatch_routing(self) -> None:
        """Test that print_result_based_on_format routes to the correct method."""
        context = DummyOutputContext(output_format="json")

        context._print_json = MagicMock()  # type: ignore
        context._print_yaml = MagicMock()  # type: ignore

        context.print_result_based_on_format({"key": "value"})

        context._print_json.assert_called_once_with({"key": "value"}, {})
        context._print_yaml.assert_not_called()

    def test_print_json_with_response_object(self) -> None:
        """Test that _print_json serializes a Response and passes a JSON string to print_json."""
        import json

        context = DummyOutputContext()
        mock_response = MagicMock(spec=Response)
        mock_response.to_json.return_value = {"success": True, "message": "Success"}

        context._print_json(mock_response, options={"filter_value": "ignore_me", "color": "red"})

        context.console.print_json.assert_called_once_with(
            json.dumps({"success": True, "message": "Success"}), color="red"
        )

    def test_print_json_with_non_serializable_data(self) -> None:
        """Test that _print_json falls back gracefully for non-JSON-serializable objects."""
        import json

        context = DummyOutputContext()

        class _DomainObject:
            # __slots__ suppresses __dict__ so the encoder falls through to str().
            __slots__ = ()

            def __str__(self):
                return "DomainObject()"

        mock_response = MagicMock(spec=Response)
        mock_response.to_json.return_value = {"success": True, "data": _DomainObject()}

        context._print_json(mock_response, options={})

        args, _ = context.console.print_json.call_args
        parsed = json.loads(args[0])
        assert parsed["success"] is True
        assert isinstance(parsed["data"], str)

    @patch("pyclif.core.mixins.output.Syntax")
    def test_print_yaml_with_dict(self, mock_syntax: MagicMock) -> None:
        """Test that _print_yaml converts a dict to YAML and uses rich Syntax."""
        context = DummyOutputContext()
        data = {"name": "Alice"}

        context._print_yaml(data, options={})

        mock_syntax.assert_called_once()
        yaml_content = mock_syntax.call_args[0][0]
        assert "name: Alice" in yaml_content

        context.console.print.assert_called_once()

    def test_print_table_with_response(self) -> None:
        """Test that _print_table invokes the to_table method of a Response."""
        context = DummyOutputContext()
        mock_response = MagicMock(spec=Response)
        mock_response.to_table.return_value = "Mocked Table String"

        context._print_table(mock_response, options={})

        mock_response.to_table.assert_called_once()
        context.console.print.assert_called_once_with("Mocked Table String")

    def test_print_table_with_callback(self) -> None:
        """Test that _print_table uses the provided callback for non-Response objects."""
        context = DummyOutputContext()
        mock_callback = MagicMock(return_value="Formatted By Callback")
        data = {"id": 1}

        context._print_table(data, options={"callback": mock_callback})

        mock_callback.assert_called_once_with(data)
        context.console.print.assert_called_once_with("Formatted By Callback")

    def test_print_rich_with_response(self) -> None:
        """Test that _print_rich invokes the to_rich method of a Response."""
        context = DummyOutputContext()
        mock_response = MagicMock(spec=Response)
        mock_response.to_rich.return_value = "Mocked Rich Output"

        context._print_rich(mock_response, options={})

        mock_response.to_rich.assert_called_once()
        context.console.print.assert_called_once_with("Mocked Rich Output")

    def test_print_raw_with_filter(self) -> None:
        """Test that _print_raw correctly applies the filter_value option on dicts."""
        context = DummyOutputContext()
        data = {"user": "Bob", "age": 30}

        context._print_raw(data, options={"filter_value": "user"})
        context.console.print.assert_called_with("Bob")

        context._print_raw(data, options={"filter_value": "email", "default_filter_value": "N/A"})
        context.console.print.assert_called_with("N/A")

    def test_print_raw_fallback(self) -> None:
        """Test that _print_raw falls back to printing the whole object if no filter matches."""
        context = DummyOutputContext()
        data = ["list", "of", "strings"]

        context._print_raw(data, options={"filter_value": "user"})
        context.console.print.assert_called_with(data)
