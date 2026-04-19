"""Unit tests for ScaffoldingTable."""

from unittest.mock import MagicMock

import pytest

from pyclif.apps.project.tables import ScaffoldingTable


@pytest.fixture
def response_factory():
    """Return a factory that builds a mock Response with given files and message."""

    def _make(files: list[dict], message: str = "Project 'my-app' created."):
        response = MagicMock()
        response.message = message
        response.data = {"files": files}
        return response

    return _make


class TestScaffoldingTable:
    """Test suite for ScaffoldingTable."""

    def test_created_action_has_sparkles(self, response_factory) -> None:
        """Created files show the sparkles emoji label."""
        table = ScaffoldingTable(response_factory([{"file": "a.py", "action": "created"}]))
        assert table.table.row_count == 1

    def test_modified_action_has_pencil(self, response_factory) -> None:
        """Modified files show the pencil emoji label."""
        table = ScaffoldingTable(response_factory([{"file": "a.py", "action": "modified"}]))
        assert table.table.row_count == 1

    def test_title_from_response_message(self, response_factory) -> None:
        """Table title matches the response message."""
        table = ScaffoldingTable(response_factory([], message="App 'repos' created."))
        assert table.table.title == "App 'repos' created."

    def test_caption_plural(self, response_factory) -> None:
        """Caption uses plural form for more than one file."""
        files = [{"file": f"f{i}.py", "action": "created"} for i in range(3)]
        table = ScaffoldingTable(response_factory(files))
        assert table.table.caption == "3 files touched"

    def test_caption_singular(self, response_factory) -> None:
        """Caption uses singular form for exactly one file."""
        table = ScaffoldingTable(response_factory([{"file": "a.py", "action": "created"}]))
        assert table.table.caption == "1 file touched"

    def test_empty_files(self, response_factory) -> None:
        """Empty file list produces a table with no rows."""
        table = ScaffoldingTable(response_factory([]))
        assert table.table.row_count == 0
