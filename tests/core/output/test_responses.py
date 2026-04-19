"""Unit tests for the Response class in the output module."""

from unittest.mock import MagicMock

import pytest

from pyclif.core.output.responses import Response


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
