"""Unit tests for the Response and OperationResult classes in the output module."""

from unittest.mock import MagicMock

import pytest

from pyclif.core.output.responses import OperationResult, Response


class TestOperationResult:
    """Test suite for OperationResult."""

    def test_ok_sets_success_true(self) -> None:
        """OperationResult.ok produces a successful result with error_code 0."""
        result = OperationResult.ok("file.py")
        assert result.success is True
        assert result.error_code == 0
        assert result.item == "file.py"

    def test_ok_carries_data(self) -> None:
        """OperationResult.ok stores the data payload."""
        result = OperationResult.ok("file.py", data={"action": "created"})
        assert result.data == {"action": "created"}

    def test_error_sets_success_false(self) -> None:
        """OperationResult.error produces a failed result."""
        result = OperationResult.error("file.py", "already exists")
        assert result.success is False
        assert result.message == "already exists"
        assert result.error_code == 1

    def test_error_custom_error_code(self) -> None:
        """OperationResult.error respects a custom error_code."""
        result = OperationResult.error("file.py", "conflict", error_code=2)
        assert result.error_code == 2


class TestResponseFromResults:
    """Test suite for Response.from_results."""

    def test_all_success_produces_success_response(self) -> None:
        """from_results returns success=True when all results succeeded."""
        results = [OperationResult.ok("a.py"), OperationResult.ok("b.py")]
        response = Response.from_results(results)
        assert response.success is True
        assert response.error_code is None

    def test_one_failure_produces_failed_response(self) -> None:
        """from_results returns success=False when any result failed."""
        results = [
            OperationResult.ok("a.py"),
            OperationResult.error("b.py", "conflict", error_code=2),
        ]
        response = Response.from_results(results)
        assert response.success is False
        assert response.error_code == 2

    def test_error_code_from_first_failure(self) -> None:
        """error_code is taken from the first failed result."""
        results = [
            OperationResult.error("a.py", "err", error_code=3),
            OperationResult.error("b.py", "err", error_code=5),
        ]
        response = Response.from_results(results)
        assert response.error_code == 3

    def test_results_stored_in_data(self) -> None:
        """All OperationResult objects are accessible via data['results']."""
        results = [OperationResult.ok("a.py")]
        response = Response.from_results(results)
        assert response.data["results"] == results

    def test_fixed_message_is_used(self) -> None:
        """message is used regardless of outcome."""
        results = [OperationResult.ok("a.py")]
        response = Response.from_results(results, message="Project created.")
        assert response.message == "Project created."

    def test_success_message_on_success(self) -> None:
        """success_message is used when all results succeeded."""
        results = [OperationResult.ok("a.py")]
        response = Response.from_results(
            results, success_message="All good.", failure_message="Bad."
        )
        assert response.message == "All good."

    def test_failure_message_on_failure(self) -> None:
        """failure_message is used when at least one result failed."""
        results = [OperationResult.error("a.py", "conflict")]
        response = Response.from_results(
            results, success_message="All good.", failure_message="Bad."
        )
        assert response.message == "Bad."

    def test_fixed_message_takes_precedence_over_success_message(self) -> None:
        """message overrides success_message / failure_message."""
        results = [OperationResult.ok("a.py")]
        response = Response.from_results(results, message="Fixed.", success_message="Good.")
        assert response.message == "Fixed."

    def test_default_message_success(self) -> None:
        """Default message reports success count when no message is provided."""
        results = [OperationResult.ok("a.py"), OperationResult.ok("b.py")]
        response = Response.from_results(results)
        assert "2" in response.message

    def test_default_message_failure(self) -> None:
        """Default message reports failure ratio when no message is provided."""
        results = [
            OperationResult.ok("a.py"),
            OperationResult.error("b.py", "conflict"),
        ]
        response = Response.from_results(results)
        assert "1/2" in response.message

    def test_table_callback_is_set(self) -> None:
        """from_results forwards the table callback to callback_table_output."""
        mock_table = MagicMock()
        results = [OperationResult.ok("a.py")]
        response = Response.from_results(results, table=mock_table)
        assert response.callback_table_output is mock_table


class MockDataModel:
    """Mock model with a to_dict method for serialization testing."""

    def to_dict(self) -> dict:
        """Return a dictionary representation of the mock model.

        Returns:
            dict: A simple dictionary with a mocked key and value.
        """
        return {"mock_key": "mock_value"}


class TestResponse:
    """Test suite for the Response class."""

    def test_initialization_defaults(self) -> None:
        """Test that a Response initializes with correct default values."""
        response = Response(success=True, message="Operation successful")

        assert response.success is True
        assert response.message == "Operation successful"
        assert response.data == {}
        assert response.error_code is None
        assert response.callback_table_output is None
        assert response.callback_rich_output is None

    def test_to_dict_excludes_defaults(self) -> None:
        """Test that to_dict returns only fields that differ from their default values."""
        response = Response(success=True, message="Test dict")
        result = response.to_dict()

        assert "success" in result
        assert "message" in result
        assert "data" in result
        assert "error_code" not in result

    def test_to_json_removes_non_serializable_fields(self) -> None:
        """Test that to_json excludes callback fields and returns serializable data."""
        mock_table_callback = MagicMock()
        mock_rich_callback = MagicMock()

        response = Response(
            success=False,
            message="An error occurred",
            error_code=404,
            callback_table_output=mock_table_callback,
            callback_rich_output=mock_rich_callback,
        )

        result = response.to_json()

        assert result["success"] is False
        assert result["message"] == "An error occurred"
        assert result["error_code"] == 404
        assert "callback_table_output" not in result
        assert "callback_rich_output" not in result

    def test_serialize_data_with_nested_objects(self) -> None:
        """Test that objects with a to_dict method are properly serialized inside data."""
        mock_object = MockDataModel()
        response = Response(
            success=True,
            message="Data fetch success",
            data={"user": mock_object, "status": "active"},
        )

        result = response.to_json()

        assert "data" in result
        assert result["data"]["status"] == "active"
        assert result["data"]["user"] == {"mock_key": "mock_value"}

    def test_to_table_with_callback(self) -> None:
        """Test that to_table executes the callback_table_output if provided."""
        mock_callback = MagicMock(return_value="Table Output")
        response = Response(success=True, message="Table test", callback_table_output=mock_callback)

        assert response.to_table() == "Table Output"
        mock_callback.assert_called_once_with(response)

    def test_to_table_without_callback_raises_error(self) -> None:
        """Test that to_table raises a RuntimeError when no callback is provided."""
        response = Response(success=True, message="No callback test")

        with pytest.raises(RuntimeError, match="No Callback to generate table output available"):
            response.to_table()

    def test_to_rich_with_callback(self) -> None:
        """Test that to_rich executes the callback_rich_output if provided."""
        mock_callback = MagicMock(return_value="Rich Output")
        response = Response(success=True, message="Rich test", callback_rich_output=mock_callback)

        assert response.to_rich() == "Rich Output"
        mock_callback.assert_called_once_with(response)

    def test_to_rich_without_callback_raises_error(self) -> None:
        """Test that to_rich raises a RuntimeError when no callback is provided."""
        response = Response(success=True, message="No callback test")

        with pytest.raises(RuntimeError, match="No Callback to generate rich output available"):
            response.to_rich()
