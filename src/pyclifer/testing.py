"""Testing utilities for pyclifer applications.

Import from this module in your test files:

    from pyclifer.testing import invoke, CliResult

Note: pytest is an optional dependency — this module is not re-exported from
pyclifer.__init__ to avoid making pytest a runtime dependency.
"""

from __future__ import annotations

import json
from typing import Any

import yaml
from click.testing import CliRunner, Result


class CliResult:
    """Typed wrapper around click.testing.Result.

    Provides convenient accessors for common test assertions without
    requiring direct access to Click internals.
    """

    def __init__(self, result: Result) -> None:
        """Wrap a Click test result.

        Args:
            result: The raw Click CliRunner result.
        """
        self._result = result

    @property
    def exit_code(self) -> int:
        """Return the command exit code."""
        return self._result.exit_code

    @property
    def output(self) -> str:
        """Return the full stdout output."""
        return self._result.output

    @property
    def stderr(self) -> str:
        """Return the stderr output captured separately from stdout."""
        return self._result.stderr

    @property
    def exception(self) -> BaseException | None:
        """Return the unhandled exception, or None when the command exited cleanly."""
        return self._result.exception

    @property
    def json(self) -> Any:
        """Parse stdout as JSON and return the result.

        Returns:
            The parsed JSON value.

        Raises:
            ValueError: When stdout is not valid JSON.
        """
        try:
            return json.loads(self._result.output)
        except json.JSONDecodeError as exc:
            raise ValueError(f"output is not valid JSON. Got:\n{self._result.output}") from exc

    @property
    def yaml(self) -> Any:
        """Parse stdout as YAML and return the result.

        Returns:
            The parsed YAML value.

        Raises:
            ValueError: When stdout is not valid YAML.
        """
        try:
            return yaml.safe_load(self._result.output)
        except yaml.YAMLError as exc:
            raise ValueError(f"output is not valid YAML. Got:\n{self._result.output}") from exc


def invoke(
    cli: Any,
    args: list[str],
    *,
    input: str | None = None,
    env: dict[str, str] | None = None,
    catch_exceptions: bool = True,
) -> CliResult:
    """Invoke a pyclifer CLI command in an isolated test environment.

    Wraps Click's CliRunner with sensible defaults for pyclifer applications.

    Args:
        cli: The Click command or group to invoke.
        args: Command line arguments (same as sys.argv[1:]).
        input: Optional stdin input string.
        env: Optional environment variables to set for the invocation.
        catch_exceptions: If False, exceptions propagate instead of being
            captured in CliResult.exception. Useful for debugging.

    Returns:
        A CliResult wrapping the invocation result.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        args,
        input=input,
        env=env,
        catch_exceptions=catch_exceptions,
    )
    return CliResult(result)


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------
# These fixtures are defined as plain functions that pytest discovers when
# imported into a conftest.py. They can also be used directly.

try:
    import pytest as _pytest

    @_pytest.fixture
    def cli_runner() -> CliRunner:
        """Return a configured CliRunner."""
        return CliRunner()

    @_pytest.fixture
    def cli_invoke():
        """Return the pyclifer invoke() helper pre-configured for testing."""
        return invoke

except ImportError:
    # pytest not installed — fixtures not available, but invoke() and CliResult still work
    pass
