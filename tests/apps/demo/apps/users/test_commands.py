"""CLI integration tests for user commands — invoked via pyclifer.testing through the full app."""

from __future__ import annotations

import datetime
import importlib
from unittest.mock import MagicMock, patch

import pytest

from pyclifer.apps.demo.apps.users.models import User
from pyclifer.cli import app
from pyclifer.testing import invoke

_demo_context_mod = importlib.import_module("pyclifer.apps.demo.core.context")
_users_iface_mod = importlib.import_module("pyclifer.apps.demo.apps.users.interfaces")

_DT = datetime.datetime(2024, 1, 1)


def _user(**kwargs) -> User:
    return User(**{"username": "alice", "email": "alice@example.com", "created_at": _DT, **kwargs})


@pytest.fixture
def storage() -> MagicMock:
    return MagicMock()


def _run(storage, *args, **kwargs):
    """Invoke an app command with Storage mocked."""
    with patch.object(_demo_context_mod, "Storage", return_value=storage):
        return invoke(app, list(args), **kwargs)


class TestListUsersCommand:
    def test_success_with_users(self, storage):
        storage.get_users.return_value = [_user()]
        result = _run(storage, "demo", "users", "list")
        assert result.exit_code == 0

    def test_empty_shows_no_dataset(self, storage):
        storage.get_users.side_effect = [[], []]
        result = _run(storage, "demo", "users", "list")
        assert result.exit_code == 0

    def test_json_output_includes_username(self, storage):
        storage.get_users.return_value = [_user(username="carol")]
        result = _run(storage, "--output-format", "json", "demo", "users", "list")
        assert result.exit_code == 0
        data = result.json
        assert data["data"]["results"][0]["username"] == "carol"


class TestWhoamiCommand:
    def test_success_exits_zero(self, storage):
        storage.get_user.return_value = _user()
        with patch.object(_users_iface_mod.os, "getenv", return_value="alice"):
            result = _run(storage, "demo", "users", "whoami")
        assert result.exit_code == 0

    def test_json_output_shows_username(self, storage):
        storage.get_user.return_value = _user(username="alice")
        with patch.object(_users_iface_mod.os, "getenv", return_value="alice"):
            result = _run(storage, "--output-format", "json", "demo", "users", "whoami")
        assert result.exit_code == 0
        data = result.json
        assert data["data"]["results"][0]["username"] == "alice"

    def test_creates_profile_when_user_absent(self, storage):
        storage.get_user.return_value = None
        with patch.object(_users_iface_mod.os, "getenv", return_value="newperson"):
            result = _run(storage, "demo", "users", "whoami")
        assert result.exit_code == 0
        storage.upsert_user.assert_called_once()
