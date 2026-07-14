# Chargement paresseux / conditionnel des groupes de commandes

**Issue GitHub :** [#7 — Lazy / conditional command group loading](https://github.com/bahamut45/pyclifer/issues/7)

**Objectif :** Permettre de n'importer un sous-ensemble configurable de commandes qu'à leur
première invocation, pour éviter de charger des dépendances lourdes (`proxmoxer`, `redfish`,
`paramiko`, ...) chez un utilisateur qui n'active jamais les fonctionnalités correspondantes.
Généralise le pattern `CommandRegistry` / `LazyCommandGroup` de `ra-tools` sans aucun couplage à
un système de configuration particulier.

**Cas d'usage cible :**

```python
from pyclifer import app_group, CommandRegistry, pass_cli_context

registry = CommandRegistry()
registry.register("proxmox", "myapp.apps.proxmox.commands", "proxmox_group")
registry.register("redfish", "myapp.apps.redfish.commands", "redfish_group", tag="hardware")


def enabled_commands() -> list[str]:
    """Read from config/env which optional command groups the user activated."""
    return read_enabled_features_from_config()


@app_group(
    command_registry=registry,
    enabled_commands_resolver=enabled_commands,
    lazy_command_disabled_message="'{name}' n'est pas activé — voir `myapp config init`.",
)
@pass_cli_context
def cli(ctx): ...
```

```bash
myapp proxmox list        # importe myapp.apps.proxmox.commands seulement maintenant
myapp redfish list        # si "redfish" absent de enabled_commands() → message clair, pas d'import
```

**Stack :** stdlib `importlib`, `dataclasses` — aucune nouvelle dépendance.

---

## Design

### Décision 1 — Résolution paresseuse déléguée à `add_command()` existant

Point clé découvert en lisant `GlobalOptionsMixin.add_command()` et
`HandleResponseMixin.add_command()` (`core/mixins/cli.py`, `core/mixins/response.py`) : les deux
mixins déjà en place se chargent respectivement de propager les options globales/contextuelles et
d'envelopper le callback avec `returns_response`, **dès que `add_command()` est appelé**. La classe
de base Click (`add_command`) enregistre aussi la commande dans `self.commands`, ce qui sert
naturellement de cache.

`LazyCommandsMixin` n'a donc **pas** à dupliquer cette logique. Sa responsabilité se limite à :
importer l'objet `Command` à la demande, puis appeler `self.add_command(cmd, name)` — la chaîne de
MRO existante (`HandleResponseMixin` → `GlobalOptionsMixin` → base Click) s'occupe du reste,
wrapping et propagation inclus. Ceci répond à la question ouverte de l'issue sur l'ordonnancement
avec `HandleResponseMixin` : aucun ordre spécial requis, `LazyCommandsMixin` ne surcharge que
`list_commands` / `get_command`, jamais `add_command`.

### Décision 2 — `enabled_commands_resolver` retourne des noms de commandes, pas des tags

Le `tag` sur `CommandRegistry` est une métadonnée libre pour l'usage du projet consommateur (filtrer
`registry.names(tag="hardware")` pour construire son propre `enabled_commands_resolver`, par
exemple). Le mixin, lui, ne fait qu'un test d'appartenance simple :
`name in enabled_commands_resolver()`. Pas de résolveur → toutes les commandes enregistrées sont
considérées actives (comportement actuel inchangé quand la feature n'est pas utilisée).

### Décision 3 — Message d'aide configurable, exception `UsageError`

Quand une commande existe dans le registre mais n'est pas dans la liste résolue, on lève
`click_extra.UsageError(self.lazy_command_disabled_message.format(name=name))` plutôt que de
retourner `None` silencieusement (`None` ferait retomber sur le "no such command" générique de
Click, qui ne distingue pas "commande inconnue" de "commande désactivée" — perte d'information
utile pour l'utilisateur).

### Décision 4 — Portée : lien avec le scaffolding hors sujet

Comme suggéré dans l'issue, l'intégration avec `pyclifer project add integration` (activer une
intégration générée seulement si sa config est présente) est explorée dans un ticket séparé une
fois ce mixin de base posé. Pas dans ce spec.

---

## Fichiers à modifier

| Fichier                            | Changement                                                            |
|-------------------------------------|------------------------------------------------------------------------|
| `src/pyclifer/core/registry.py` (nouveau) | `CommandRegistry`, `CommandEntry`                                |
| `src/pyclifer/core/mixins/cli.py`  | Ajouter `LazyCommandsMixin`                                            |
| `src/pyclifer/core/mixins/__init__.py` | Exporter `LazyCommandsMixin`                                       |
| `src/pyclifer/core/classes.py`     | `GroupConfig` : 3 nouveaux champs ; `LazyCommandsMixin` dans les bases de `PycliferExtraGroup`/`PycliferRichGroup` |
| `src/pyclifer/core/decorators.py`  | `GroupDecorator._configure_lazy_commands()` — wiring registry/resolver/message sur l'instance du groupe |
| `src/pyclifer/__init__.py`         | Exporter `CommandRegistry`                                             |
| `tests/core/test_registry.py` (nouveau) | Tests unitaires `CommandRegistry`                                 |
| `tests/core/mixins/test_cli.py`    | Nouvelle classe `TestLazyCommandsMixin`                                |
| `docs/api/classes.md`              | Documenter les nouveaux champs de `GroupConfig`                        |
| `docs/api/mixins.md`               | Documenter `LazyCommandsMixin`                                         |
| `docs/how-to/lazy-commands.md` (nouveau) | Guide d'usage                                                    |
| `mkdocs.yml`                       | Ajouter la nouvelle page au `nav`                                       |

---

## Tâche 1 : Créer la branche et écrire les tests échouants pour `CommandRegistry`

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/lazy-command-loading
```

- [ ] **Étape 2 : Écrire les tests dans `tests/core/test_registry.py`**

```python
import pytest

from pyclifer.core.registry import CommandRegistry


class TestCommandRegistry:
    """CommandRegistry maps command names to lazily-importable targets."""

    def test_register_and_resolve_returns_the_target_object(self):
        registry = CommandRegistry()
        registry.register("hello", "tests.fixtures.lazy_targets", "hello_command")

        resolved = registry.resolve("hello")

        from tests.fixtures.lazy_targets import hello_command

        assert resolved is hello_command

    def test_resolve_unknown_name_raises_key_error(self):
        registry = CommandRegistry()

        with pytest.raises(KeyError, match="unknown"):
            registry.resolve("unknown")

    def test_names_returns_all_registered_names(self):
        registry = CommandRegistry()
        registry.register("a", "mod.a", "cmd", tag="default")
        registry.register("b", "mod.b", "cmd", tag="extra")

        assert sorted(registry.names()) == ["a", "b"]

    def test_names_filters_by_tag(self):
        registry = CommandRegistry()
        registry.register("a", "mod.a", "cmd", tag="default")
        registry.register("b", "mod.b", "cmd", tag="extra")

        assert registry.names(tag="extra") == ["b"]

    def test_contains_reflects_registered_names(self):
        registry = CommandRegistry()
        registry.register("a", "mod.a", "cmd")

        assert "a" in registry
        assert "b" not in registry
```

- [ ] **Étape 3 : Créer le fixture module `tests/fixtures/lazy_targets.py`**

```python
"""Import target used by CommandRegistry tests."""

import click_extra


@click_extra.command()
def hello_command() -> None:
    """Say hello."""
    click_extra.echo("hello")
```

- [ ] **Étape 4 : Confirmer l'échec**

```bash
python -m pytest tests/core/test_registry.py -v
```

Attendu : `ModuleNotFoundError: No module named 'pyclifer.core.registry'`

---

## Tâche 2 : Implémenter `CommandRegistry`

**Fichier :** `src/pyclifer/core/registry.py` (nouveau)

- [ ] **Étape 1 : Écrire le module**

```python
"""Registry mapping command names to lazily-importable command objects."""

import importlib
from dataclasses import dataclass
from typing import Any


@dataclass
class CommandEntry:
    """A single lazy-import target for a registered command."""

    module_path: str
    attribute: str
    tag: str = "default"


class CommandRegistry:
    """Maps command names to (module, attribute, tag) targets, resolved on demand.

    Carries no knowledge of any particular business domain — the tag is
    free-form and only meaningful to the project registering commands (e.g.
    to build its own enabled_commands_resolver).
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._entries: dict[str, CommandEntry] = {}

    def register(self, name: str, module_path: str, attribute: str, tag: str = "default") -> None:
        """Register a lazy command target.

        Args:
            name: The CLI-visible command name.
            module_path: Dotted path of the module to import on first use.
            attribute: Name of the Command object inside that module.
            tag: Free-form label for the caller's own filtering logic.
        """
        self._entries[name] = CommandEntry(module_path=module_path, attribute=attribute, tag=tag)

    def names(self, tag: str | None = None) -> list[str]:
        """Return registered command names, optionally filtered by tag.

        Args:
            tag: If given, only names registered under this tag are returned.

        Returns:
            The list of matching command names.
        """
        if tag is None:
            return list(self._entries)
        return [name for name, entry in self._entries.items() if entry.tag == tag]

    def resolve(self, name: str) -> Any:
        """Import the target module and return the registered command object.

        Args:
            name: The command name to resolve.

        Returns:
            The Command object found at the registered attribute.

        Raises:
            KeyError: When name was never registered.
        """
        if name not in self._entries:
            raise KeyError(f"unknown command '{name}' in registry")
        entry = self._entries[name]
        module = importlib.import_module(entry.module_path)
        return getattr(module, entry.attribute)

    def __contains__(self, name: str) -> bool:
        """Return whether name is registered."""
        return name in self._entries
```

- [ ] **Étape 2 : Confirmer le succès**

```bash
python -m pytest tests/core/test_registry.py -v
```

---

## Tâche 3 : Écrire les tests échouants pour `LazyCommandsMixin`

**Fichier :** `tests/core/mixins/test_cli.py` (ajouter une classe)

```python
import click_extra
import pytest

from pyclifer.core.mixins.cli import LazyCommandsMixin
from pyclifer.core.registry import CommandRegistry


class _LazyGroup(LazyCommandsMixin, click_extra.Group):
    """Minimal group under test."""


class TestLazyCommandsMixin:
    """LazyCommandsMixin resolves registered commands on first use."""

    def test_get_command_imports_and_caches_on_first_call(self, monkeypatch):
        registry = CommandRegistry()
        registry.register("hello", "tests.fixtures.lazy_targets", "hello_command")
        group = _LazyGroup(name="cli")
        group.command_registry = registry

        ctx = click_extra.Context(group)
        cmd = group.get_command(ctx, "hello")

        assert cmd is not None
        assert "hello" in group.commands  # cached via add_command()

    def test_list_commands_includes_registry_entries_without_importing(self):
        registry = CommandRegistry()
        registry.register("hello", "tests.fixtures.lazy_targets", "hello_command")
        group = _LazyGroup(name="cli")
        group.command_registry = registry

        ctx = click_extra.Context(group)

        assert "hello" in group.list_commands(ctx)
        assert "hello" not in group.commands  # not imported yet

    def test_get_command_returns_none_for_names_outside_registry_and_commands(self):
        group = _LazyGroup(name="cli")
        group.command_registry = CommandRegistry()

        ctx = click_extra.Context(group)

        assert group.get_command(ctx, "nope") is None

    def test_disabled_command_raises_usage_error_with_custom_message(self):
        registry = CommandRegistry()
        registry.register("hello", "tests.fixtures.lazy_targets", "hello_command")
        group = _LazyGroup(name="cli")
        group.command_registry = registry
        group.enabled_commands_resolver = lambda: []
        group.lazy_command_disabled_message = "'{name}' is disabled."

        ctx = click_extra.Context(group)

        with pytest.raises(click_extra.UsageError, match="'hello' is disabled."):
            group.get_command(ctx, "hello")

    def test_enabled_resolver_allows_listed_command(self):
        registry = CommandRegistry()
        registry.register("hello", "tests.fixtures.lazy_targets", "hello_command")
        group = _LazyGroup(name="cli")
        group.command_registry = registry
        group.enabled_commands_resolver = lambda: ["hello"]

        ctx = click_extra.Context(group)

        assert group.get_command(ctx, "hello") is not None

    def test_without_registry_behaves_like_plain_group(self):
        group = _LazyGroup(name="cli")

        ctx = click_extra.Context(group)

        assert group.get_command(ctx, "anything") is None
        assert group.list_commands(ctx) == []
```

- [ ] **Confirmer l'échec**

```bash
python -m pytest tests/core/mixins/test_cli.py::TestLazyCommandsMixin -v
```

Attendu : `ImportError: cannot import name 'LazyCommandsMixin'`

---

## Tâche 4 : Implémenter `LazyCommandsMixin`

**Fichier :** `src/pyclifer/core/mixins/cli.py` (ajouter à la suite de `GlobalOptionsMixin`)

```python
from collections.abc import Callable

from pyclifer.core.registry import CommandRegistry


class LazyCommandsMixin:
    """Mixin that resolves registered commands from a CommandRegistry on first use.

    Commands not yet resolved are absent from self.commands until their first
    get_command() call, at which point they are imported and registered via
    add_command() — reusing whatever wrapping/propagation the rest of the
    mixin stack (HandleResponseMixin, GlobalOptionsMixin) already applies.
    """

    command_registry: CommandRegistry | None = None
    enabled_commands_resolver: Callable[[], list[str]] | None = None
    lazy_command_disabled_message: str = "Command '{name}' is not enabled."

    def _is_command_enabled(self, name: str) -> bool:
        """Return whether name passes the enabled_commands_resolver filter."""
        if self.enabled_commands_resolver is None:
            return True
        return name in self.enabled_commands_resolver()

    def list_commands(self, ctx: click_extra.Context) -> list[str]:
        """Return eagerly-registered commands plus enabled registry entries.

        Args:
            ctx: The current Click context.

        Returns:
            Sorted, deduplicated list of visible command names.
        """
        # noinspection PyUnresolvedReferences
        names = set(super().list_commands(ctx))
        if self.command_registry is not None:
            names.update(n for n in self.command_registry.names() if self._is_command_enabled(n))
        return sorted(names)

    def get_command(self, ctx: click_extra.Context, name: str) -> click_extra.Command | None:
        """Resolve name from the registry on first use, else defer to super().

        Args:
            ctx: The current Click context.
            name: The requested command name.

        Returns:
            The resolved Command, or None if unknown.

        Raises:
            click_extra.UsageError: When name is registered but not enabled.
        """
        if self.command_registry is None or name in self.commands or name not in self.command_registry:
            # noinspection PyUnresolvedReferences
            return super().get_command(ctx, name)

        if not self._is_command_enabled(name):
            raise click_extra.UsageError(self.lazy_command_disabled_message.format(name=name))

        cmd = self.command_registry.resolve(name)
        self.add_command(cmd, name)  # noqa — triggers response wrapping + option propagation
        # noinspection PyUnresolvedReferences
        return super().get_command(ctx, name)
```

- [ ] Ajouter `import click_extra` en tête de fichier s'il n'y est pas déjà (il y est déjà).
- [ ] Confirmer le succès :

```bash
python -m pytest tests/core/mixins/test_cli.py::TestLazyCommandsMixin -v
```

---

## Tâche 5 : Wiring — `GroupConfig`, classes composites, export public

- [ ] **Étape 1 : `src/pyclifer/core/mixins/__init__.py`** — ajouter `LazyCommandsMixin` aux exports.

- [ ] **Étape 2 : `src/pyclifer/core/classes.py`**

Ajouter dans `GroupConfig` (section "Feature flags" ou nouvelle section) :

```python
    # Lazy command loading
    command_registry: CommandRegistry | None = None
    enabled_commands_resolver: Callable[[], list[str]] | None = None
    lazy_command_disabled_message: str = "Command '{name}' is not enabled."
```

Mettre à jour les bases des deux classes composites :

```python
class PycliferExtraGroup(HandleResponseMixin, GlobalOptionsMixin, LazyCommandsMixin, click_extra.ExtraGroup):
    ...


class PycliferRichGroup(HandleResponseMixin, GlobalOptionsMixin, LazyCommandsMixin, RichGroup):
    ...
```

Importer `CommandRegistry` et `LazyCommandsMixin` en tête de fichier.

- [ ] **Étape 3 : `src/pyclifer/core/decorators.py`**

Ajouter une méthode sur `GroupDecorator`, appelée dans `__call__` juste après
`_configure_handle_response` :

```python
    def _configure_lazy_commands(self, f: click_extra.Group) -> None:
        """Propagate the command registry and resolver to the group instance.

        Args:
            f: The Click group instance to configure.
        """
        if self.config.command_registry is not None:
            f.command_registry = self.config.command_registry
            f.enabled_commands_resolver = self.config.enabled_commands_resolver
            f.lazy_command_disabled_message = self.config.lazy_command_disabled_message
```

Et dans `__call__` :

```python
        self._configure_handle_response(f)
        self._configure_lazy_commands(f)
        return f
```

- [ ] **Étape 4 : `src/pyclifer/__init__.py`** — exporter `CommandRegistry` dans `__all__` et le
  re-export depuis `pyclifer.core.registry`.

---

## Tâche 6 : Tests d'intégration bout-en-bout

**Fichier :** `tests/core/test_decorators.py` (ou un nouveau `tests/core/test_lazy_commands_integration.py`)

- [ ] Écrire un test utilisant `@app_group(command_registry=..., enabled_commands_resolver=...)`
  et `pyclifer.testing.invoke()` pour vérifier :
  - une commande activée s'exécute normalement (`exit_code == 0`) ;
  - une commande désactivée renvoie le message custom et un exit code non nul ;
  - une commande absente du registre garde le comportement Click standard ("No such command").

```bash
python -m pytest tests/core/test_decorators.py -v -k lazy
```

---

## Tâche 7 : Vérification complète

- [ ] **Étape 1 : Tous les tests**

```bash
python -m pytest tests/ -v
```

- [ ] **Étape 2 : Lint**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

---

## Tâche 8 : Documentation

- [ ] **`docs/how-to/lazy-commands.md`** (nouveau) — reprendre l'exemple du "Cas d'usage cible"
  ci-dessus, expliquer `CommandRegistry`, `enabled_commands_resolver`, le message d'erreur
  configurable, et la mise en garde sur l'ordre de résolution (le registre ne remplace pas
  `add_command()` classique, il le complète).
- [ ] **`docs/api/classes.md`** — documenter les 3 nouveaux champs de `GroupConfig` et
  `CommandRegistry`.
- [ ] **`docs/api/mixins.md`** — documenter `LazyCommandsMixin`.
- [ ] **`mkdocs.yml`** — ajouter `how-to/lazy-commands.md` au `nav`.
- [ ] **Étape finale :**

```bash
mkdocs build --strict
```

---

## Tâche 9 : Commit

```bash
git add src/ tests/ docs/ mkdocs.yml .claude/specs/09-lazy-command-loading.md
git commit -m "$(cat <<'EOF'
✨ feat(registry): add lazy command group loading

- CommandRegistry maps command names to (module, attribute, tag) lazy-import targets
- LazyCommandsMixin resolves commands on first get_command() via add_command(),
  reusing existing response-wrapping and global-option propagation
- Disabled commands (per enabled_commands_resolver) raise UsageError with a
  configurable message instead of falling back to Click's generic "no such command"
- Closes #7
EOF
)"
```

Fusionner dans `main` après validation utilisateur, puis supprimer la branche.