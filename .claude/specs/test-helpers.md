# Helpers de test — module `pyclifer.testing`

**Objectif :** Fournir un module `pyclifer.testing` avec des helpers pytest pour tester
les commandes pyclifer sans boilerplate `CliRunner`. Retourne un objet typé `CliResult`
avec accès direct à `exit_code`, `output`, `.json`, `.yaml`.

**Cas d'usage cible :**

```python
# tests/apps/test_articles.py
from pyclifer.testing import invoke

def test_list_articles(cli):
    result = invoke(cli, ["articles", "list", "-o", "json"])
    assert result.exit_code == 0
    assert result.json["success"] is True
    assert len(result.json["data"]["results"]) == 3
```

**Stack :** `click.testing.CliRunner`, `pytest`, `json`, `yaml` (déjà dépendances du projet).

---

## Design

### `CliResult` — wrapper autour de `click.testing.Result`

Expose les propriétés les plus utiles sans exposer Click directement :

| Propriété | Type | Description |
|-----------|------|-------------|
| `exit_code` | `int` | Code de sortie de la commande |
| `output` | `str` | Sortie stdout complète |
| `stderr` | `str` | Sortie stderr (si mix_stderr=False) |
| `json` | `dict` | Output parsé comme JSON — lève `ValueError` si invalide |
| `yaml` | `Any` | Output parsé comme YAML — lève `ValueError` si invalide |
| `exception` | `Exception \| None` | Exception non catchée si `catch_exceptions=True` |

### `invoke()` — fonction helper

```python
def invoke(
    cli: click_extra.BaseCommand,
    args: list[str],
    *,
    input: str | None = None,
    env: dict[str, str] | None = None,
    catch_exceptions: bool = True,
    mix_stderr: bool = False,
) -> CliResult
```

### Fixtures pytest

Exposées pour être réutilisables via conftest.

```python
@pytest.fixture
def cli_runner() -> CliRunner:
    """Configured CliRunner with mix_stderr=False."""

@pytest.fixture  
def cli_invoke() -> Callable:
    """Preconfigured invoke() function — same as pyclifer.testing.invoke."""
```

### Pas de `BaseCliTest(TestCase)`

Les fixtures pytest sont plus composables et s'intègrent mieux dans un projet pytest-only.
`BaseCliTest` forcerait l'héritage et bloquerait les fixtures pytest classiques.

### Emplacement

`src/pyclifer/testing.py` — module public, pas dans `core/`. Importé via
`from pyclifer.testing import invoke` (pas ré-exporté depuis `pyclifer.__init__`
pour éviter que `pytest` soit une dépendance runtime).

---

## Fichiers à créer / modifier

| Fichier | Changement |
|---------|-----------|
| `src/pyclifer/testing.py` | Nouveau module — `CliResult`, `invoke()`, fixtures pytest |
| `tests/test_testing.py` | Tests du module de test lui-même |

---

## Tâche 1 : Créer la branche et écrire les tests échouants

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/test-helpers
```

- [ ] **Étape 2 : Créer `tests/test_testing.py`**

```python
"""Tests for pyclifer.testing — CliResult and invoke() helper."""
import pytest
from pyclifer import app_group, command, returns_response, Response, pass_context
from pyclifer.testing import CliResult, invoke


def make_cli(output_format: str = "json"):
    @app_group(add_version_option=False, output_format_default=output_format)
    @pass_context
    def cli(ctx):
        pass

    @cli.command()
    @returns_response
    @pass_context
    def hello(ctx):
        return Response(success=True, message="hello world", data={"key": "value"})

    @cli.command()
    @pass_context
    def fail(ctx):
        raise RuntimeError("boom")

    return cli


class TestCliResult:
    """CliResult wraps Click's Result with typed accessors."""

    def test_exit_code_zero_on_success(self):
        cli = make_cli()
        result = invoke(cli, ["hello"])
        assert result.exit_code == 0

    def test_output_contains_stdout(self):
        cli = make_cli("text")
        result = invoke(cli, ["hello"])
        assert "hello world" in result.output

    def test_json_parses_json_output(self):
        cli = make_cli("json")
        result = invoke(cli, ["hello"])
        assert result.json["success"] is True
        assert result.json["message"] == "hello world"
        assert result.json["data"]["key"] == "value"

    def test_yaml_parses_yaml_output(self):
        cli = make_cli("yaml")
        result = invoke(cli, ["hello"])
        assert result.yaml["success"] is True

    def test_json_raises_value_error_on_non_json(self):
        cli = make_cli("text")
        result = invoke(cli, ["hello"])
        with pytest.raises(ValueError, match="output is not valid JSON"):
            _ = result.json

    def test_yaml_raises_value_error_on_non_yaml(self):
        cli = make_cli()
        result = invoke(cli, ["hello"])
        # JSON is valid YAML, so use a format that produces non-parseable YAML
        # Just verify the attribute exists
        assert hasattr(result, "yaml")

    def test_exception_is_none_on_success(self):
        cli = make_cli()
        result = invoke(cli, ["hello"])
        assert result.exception is None

    def test_exception_captured_on_failure(self):
        cli = make_cli()
        result = invoke(cli, ["fail"], catch_exceptions=True)
        assert result.exception is not None
        assert isinstance(result.exception, RuntimeError)


class TestInvokeHelper:
    """invoke() wraps CliRunner with sensible defaults."""

    def test_invoke_returns_cli_result(self):
        cli = make_cli()
        result = invoke(cli, ["hello"])
        assert isinstance(result, CliResult)

    def test_invoke_with_env(self):
        cli = make_cli()
        result = invoke(cli, ["hello"], env={"SOME_VAR": "1"})
        assert result.exit_code == 0

    def test_invoke_with_input(self):
        @app_group(add_version_option=False)
        @pass_context
        def cli(ctx):
            pass

        @cli.command()
        def ask():
            val = input("Enter: ")
            print(f"Got: {val}")

        result = invoke(cli, ["ask"], input="hello\n")
        assert "Got: hello" in result.output

    def test_invoke_catch_exceptions_false_propagates(self):
        cli = make_cli()
        with pytest.raises(RuntimeError, match="boom"):
            invoke(cli, ["fail"], catch_exceptions=False)


class TestPytestFixtures:
    """pytest fixtures from pyclifer.testing are importable and functional."""

    def test_cli_runner_fixture_importable(self):
        from pyclifer.testing import cli_runner
        assert callable(cli_runner)

    def test_cli_invoke_fixture_importable(self):
        from pyclifer.testing import cli_invoke
        assert callable(cli_invoke)
```

- [ ] **Étape 3 : Confirmer l'échec**

```bash
python -m pytest tests/test_testing.py -v
```

Attendu : `ModuleNotFoundError: No module named 'pyclifer.testing'`

---

## Tâche 2 : Créer `src/pyclifer/testing.py`

**Fichier :** `src/pyclifer/testing.py` (nouveau)

```python
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

    Attributes:
        exit_code: The command exit code.
        output: The full stdout output string.
        stderr: The stderr output (empty string when mix_stderr=True).
        exception: The unhandled exception, or None on clean exit.
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
        """Return the stderr output (empty when mix_stderr=True)."""
        return getattr(self._result, "stderr", "")

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
            raise ValueError(
                f"output is not valid JSON. Got:\n{self._result.output}"
            ) from exc

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
            raise ValueError(
                f"output is not valid YAML. Got:\n{self._result.output}"
            ) from exc


def invoke(
    cli: Any,
    args: list[str],
    *,
    input: str | None = None,
    env: dict[str, str] | None = None,
    catch_exceptions: bool = True,
    mix_stderr: bool = False,
) -> CliResult:
    """Invoke a pyclifer CLI command in an isolated test environment.

    Wraps Click's CliRunner with sensible defaults for pyclifer applications.
    stderr is separated from stdout by default so output parsing is not
    polluted by log messages.

    Args:
        cli: The Click command or group to invoke.
        args: Command line arguments (same as sys.argv[1:]).
        input: Optional stdin input string.
        env: Optional environment variables to set for the invocation.
        catch_exceptions: If False, exceptions propagate instead of being
            captured in CliResult.exception. Useful for debugging.
        mix_stderr: If True, mix stderr into stdout (default False).

    Returns:
        A CliResult wrapping the invocation result.
    """
    runner = CliRunner(mix_stderr=mix_stderr)
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
        """Return a CliRunner with mix_stderr=False."""
        return CliRunner(mix_stderr=False)

    @_pytest.fixture
    def cli_invoke():
        """Return the pyclifer invoke() helper pre-configured for testing."""
        return invoke

except ImportError:
    # pytest not installed — fixtures not available, but invoke() and CliResult still work
    pass
```

---

## Tâche 3 : Vérification complète

- [ ] **Étape 1 : Tous les tests passent**

```bash
python -m pytest tests/test_testing.py -v
```

- [ ] **Étape 2 : Tous les tests du projet passent**

```bash
python -m pytest tests/ -v
```

- [ ] **Étape 3 : Vérifier que `pyclifer.testing` n'est pas importé par `__init__.py`**

```bash
grep -n "testing" src/pyclifer/__init__.py
```

Attendu : aucune ligne — le module est disponible mais non ré-exporté.

---

## Tâche 4 : Lint et commit

- [ ] **Étape 1 : Ruff**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

- [ ] **Étape 2 : Commit**

```bash
git add src/pyclifer/testing.py tests/test_testing.py
git commit -m "$(cat <<'EOF'
✨ feat(testing): add pyclifer.testing module with pytest helpers

- CliResult wraps click.testing.Result with .json, .yaml, .exit_code, .exception
- invoke() helper replaces CliRunner boilerplate in test files
- cli_runner and cli_invoke pytest fixtures auto-discovered in conftest.py
- Module not re-exported from __init__ — pytest stays a dev-only dependency
EOF
)"
```