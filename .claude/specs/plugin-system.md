# Système de plugins

**Objectif :** Permettre aux applications pyclifer d'être étendues par des packages
tiers via `importlib.metadata.entry_points`, et par des modules internes via
`cli.register_plugin(group)`. Aucune modification de code dans le projet principal
pour installer un plugin.

**Cas d'usage cible :**

```python
# myapp/cli.py
@app_group(plugins_entry_point="myapp.commands", add_version_option=False)
def cli(): ...

# Projet tiers myapp-extra/pyproject.toml
[project.entry-points."myapp.commands"]
billing = "myapp_extra.billing:billing_group"

# Après pip install myapp-extra :
myapp billing list   # fonctionne automatiquement
```

```python
# Enregistrement programmatique (modules internes)
from myapp.apps.admin import admin_group
cli.register_plugin(admin_group)
```

**Stack :** `importlib.metadata` (stdlib Python 3.10+), aucune dépendance supplémentaire.

---

## Design

### Deux mécanismes indépendants

**1. Entry points** (plugins distribués)
- Déclaré via `plugins_entry_point="myapp.commands"` sur `@app_group`
- Chargé au moment de `GroupDecorator.__call__()` — avant que le groupe soit retourné
- Chaque entry point est une fonction ou un objet retournant un Click group/command
- Erreur de chargement : warning loggé, plugin ignoré (fail-soft)

**2. `register_plugin()`** (plugins internes / runtime)
- Méthode sur le groupe Click résultant
- Alias ergonomique pour `add_command()` avec validation que l'objet est un Click command
- Peut être appelé après `@app_group` retourne, avant l'invocation CLI

### Chargement fail-soft

Un plugin défaillant (import error, entry point cassé) ne doit pas faire échouer le CLI.
On log un warning et on continue. L'application reste utilisable.

### Format d'un entry point

L'entry point doit pointer vers un objet Click `Command` ou `Group`, ou une callable
sans argument qui en retourne un.

```toml
[project.entry-points."myapp.commands"]
my-plugin = "myplugin.commands:my_group"       # objet Group
other = "myplugin.commands:get_other_group"    # callable → Group
```

### `register_plugin()` vs `add_command()`

`add_command()` est l'API Click existante. `register_plugin()` est un wrapper qui :
- Accepte un Click `Command` ou `Group`
- Lève `TypeError` si l'objet n'est pas un Click command (erreur de programmation)
- Documente clairement l'intention "c'est un plugin"

---

## Fichiers à modifier

| Fichier | Changement |
|---------|-----------|
| `src/pyclifer/core/classes.py` | Ajouter `plugins_entry_point` dans `GroupConfig` ; `register_plugin()` sur les classes de groupe |
| `src/pyclifer/core/decorators.py` | `GroupDecorator._load_plugins()` appelé dans `__call__()` |
| `tests/core/test_plugins.py` | Nouveaux tests (nouveau fichier) |

---

## Tâche 1 : Créer la branche et écrire les tests échouants

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/plugin-system
```

- [ ] **Étape 2 : Créer `tests/core/test_plugins.py`**

```python
"""Tests for the pyclifer plugin system — entry_points + register_plugin()."""
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import click
from pyclifer import app_group, group, command, pass_context, returns_response, Response


def make_plugin_group(name: str, message: str):
    @group(name=name)
    @pass_context
    def plugin(ctx):
        pass

    @plugin.command()
    @returns_response
    @pass_context
    def action(ctx):
        return Response(success=True, message=message, data={})

    return plugin


def make_cli_with_entry_point(ep_group: str = "myapp.commands"):
    @app_group(add_version_option=False, plugins_entry_point=ep_group)
    @pass_context
    def cli(ctx):
        pass

    return cli


class TestEntryPointDiscovery:
    """Plugins declared via entry_points are auto-loaded at group creation."""

    def test_plugin_commands_available_after_load(self):
        billing = make_plugin_group("billing", "billing ok")

        mock_ep = MagicMock()
        mock_ep.name = "billing"
        mock_ep.load.return_value = billing

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            cli = make_cli_with_entry_point("myapp.commands")

        runner = CliRunner()
        result = runner.invoke(cli, ["billing", "action"])
        assert result.exit_code == 0
        assert "billing ok" in result.output

    def test_plugin_appears_in_help(self):
        billing = make_plugin_group("billing", "billing ok")

        mock_ep = MagicMock()
        mock_ep.name = "billing"
        mock_ep.load.return_value = billing

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            cli = make_cli_with_entry_point()

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "billing" in result.output

    def test_broken_plugin_is_skipped_with_warning(self, caplog):
        import logging
        mock_ep = MagicMock()
        mock_ep.name = "broken"
        mock_ep.load.side_effect = ImportError("missing dependency")

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            with caplog.at_level(logging.WARNING):
                cli = make_cli_with_entry_point()

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "broken" not in result.output

    def test_no_entry_point_group_loads_nothing(self):
        @app_group(add_version_option=False)
        @pass_context
        def cli(ctx):
            pass

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_callable_entry_point_is_called(self):
        billing = make_plugin_group("billing", "billing ok")

        mock_ep = MagicMock()
        mock_ep.name = "billing"
        mock_ep.load.return_value = lambda: billing  # callable factory

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            cli = make_cli_with_entry_point()

        runner = CliRunner()
        result = runner.invoke(cli, ["billing", "action"])
        assert "billing ok" in result.output


class TestRegisterPlugin:
    """register_plugin() adds a command/group to the CLI."""

    def test_register_plugin_adds_command(self):
        @app_group(add_version_option=False)
        @pass_context
        def cli(ctx):
            pass

        billing = make_plugin_group("billing", "billing registered")
        cli.register_plugin(billing)

        runner = CliRunner()
        result = runner.invoke(cli, ["billing", "action"])
        assert result.exit_code == 0
        assert "billing registered" in result.output

    def test_register_plugin_invalid_type_raises(self):
        @app_group(add_version_option=False)
        @pass_context
        def cli(ctx):
            pass

        with pytest.raises(TypeError, match="must be a Click Command or Group"):
            cli.register_plugin("not a click command")

    def test_register_plugin_is_accessible_after_registration(self):
        @app_group(add_version_option=False)
        @pass_context
        def cli(ctx):
            pass

        billing = make_plugin_group("billing", "ok")
        cli.register_plugin(billing)
        assert "billing" in cli.commands
```

- [ ] **Étape 3 : Confirmer l'échec**

```bash
python -m pytest tests/core/test_plugins.py -v
```

Attendu : `TypeError` — `plugins_entry_point` n'est pas un champ de `GroupConfig`.

---

## Tâche 2 : Ajouter `plugins_entry_point` dans `GroupConfig`

**Fichier :** `src/pyclifer/core/classes.py`

- [ ] **Étape 1 : Ajouter le champ dans `GroupConfig`**

```python
    plugins_entry_point: str | None = None
```

---

## Tâche 3 : Ajouter `register_plugin()` sur les classes de groupe

**Fichier :** `src/pyclifer/core/classes.py`

- [ ] **Étape 1 : Ajouter la méthode sur `PycliferExtraGroup`**

Dans la classe `PycliferExtraGroup`, ajouter :

```python
    def register_plugin(self, plugin: click_extra.BaseCommand) -> None:
        """Register a Click command or group as a plugin.

        Adds the plugin to this group's command list. Raises TypeError when
        the argument is not a Click command — this is a programming error, not
        a business failure.

        Args:
            plugin: A Click Command or Group to register.

        Raises:
            TypeError: When plugin is not a Click BaseCommand instance.
        """
        if not isinstance(plugin, click_extra.BaseCommand):
            raise TypeError(
                f"register_plugin() argument must be a Click Command or Group, "
                f"got {type(plugin).__name__!r}"
            )
        self.add_command(plugin)
```

- [ ] **Étape 2 : Ajouter la même méthode sur `PycliferRichGroup`**

Même implémentation — les deux classes doivent exposer `register_plugin()`.

---

## Tâche 4 : Ajouter `_load_plugins()` dans `GroupDecorator`

**Fichier :** `src/pyclifer/core/decorators.py`

- [ ] **Étape 1 : Ajouter la méthode `_load_plugins()` dans `GroupDecorator`**

```python
    def _load_plugins(self, f: click_extra.Group) -> None:
        """Discover and load plugins from importlib.metadata entry_points.

        Each entry point is loaded and registered as a subcommand. Entry points
        that fail to load are skipped with a warning — the CLI remains usable.

        If the loaded object is callable and not a Click command, it is called
        with no arguments and the result is registered instead.

        Args:
            f: The Click group to add discovered plugins to.
        """
        if not self.config.plugins_entry_point:
            return

        import importlib.metadata  # noqa: PLC0415 — stdlib, lazy for startup performance

        try:
            eps = importlib.metadata.entry_points(group=self.config.plugins_entry_point)
        except Exception:
            _log.warning(
                "Failed to query entry_points for group %r",
                self.config.plugins_entry_point,
            )
            return

        for ep in eps:
            try:
                plugin = ep.load()
                if not isinstance(plugin, click_extra.BaseCommand) and callable(plugin):
                    plugin = plugin()
                if isinstance(plugin, click_extra.BaseCommand):
                    f.add_command(plugin)
                else:
                    _log.warning(
                        "Plugin entry point %r did not return a Click command — skipped",
                        ep.name,
                    )
            except Exception:
                _log.warning(
                    "Failed to load plugin %r from entry point group %r — skipped",
                    ep.name,
                    self.config.plugins_entry_point,
                    exc_info=True,
                )
```

- [ ] **Étape 2 : Appeler `_load_plugins()` dans `GroupDecorator.__call__()`**

Après `self._configure_handle_response(f)` :

```python
        self._load_plugins(f)
```

---

## Tâche 5 : Vérification complète

- [ ] **Étape 1 : Tous les tests passent**

```bash
python -m pytest tests/ -v
```

- [ ] **Étape 2 : Test de non-régression — CLI sans entry point**

```bash
python -m pytest tests/ -v -k "not plugin"
```

---

## Tâche 6 : Documentation de l'entry point dans la docstring

**Fichier :** `src/pyclifer/core/decorators.py`

- [ ] **Étape 1 : Mettre à jour la docstring de `app_group()`**

Ajouter dans la section `Notable options` :

```
    - `plugins_entry_point` (str): Entry point group name for auto-discovering
      installed plugins (e.g., "myapp.commands"). Each entry point must resolve
      to a Click Command/Group or a callable returning one.
```

---

## Tâche 7 : Lint et commit

- [ ] **Étape 1 : Ruff**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

- [ ] **Étape 2 : Commit**

```bash
git add src/ tests/core/test_plugins.py
git commit -m "$(cat <<'EOF'
✨ feat(plugins): add entry_point discovery and register_plugin()

- GroupConfig.plugins_entry_point enables auto-discovery via importlib.metadata
- Broken plugins are skipped with a warning — CLI stays usable (fail-soft)
- Callable entry points (factory functions) are supported
- register_plugin() is an ergonomic alias for add_command() with type validation
EOF
)"
```