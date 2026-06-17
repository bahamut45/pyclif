# Middleware / Hooks avant et après commande

**Objectif :** Permettre l'enregistrement de fonctions exécutées avant et après chaque
invocation de sous-commande via `@app_group(before_invoke=[...], after_invoke=[...])`.
Couvre les hooks d'audit, d'authentification, et de logging cross-cutting.

**Cas d'usage cible :**

```python
def require_auth(ctx):
    if not ctx.meta.get("token"):
        raise click.UsageError("Non authentifié — lancez `myapp login` d'abord.")

def audit_log(ctx):
    logger.info("Command: %s", ctx.info_name)

@app_group(before_invoke=[require_auth, audit_log])
def cli(): ...
```

**Stack :** click_extra, stdlib uniquement

---

## Design

### Décision : patch sur `PycliferGroup.invoke()`

Click appelle `Group.invoke(ctx)` pour exécuter la chaîne de sous-commandes. C'est le
point d'interception minimal qui couvre **toutes** les commandes du groupe, avec ou sans
`returns_response`. L'alternative (patch dans `returns_response`) ne couvrirait pas les
commandes sans retour de `Response`.

### Signature des hooks

```python
# before_invoke : reçoit le contexte du groupe racine
# Retourner False bloque l'exécution
def my_before_hook(ctx: click_extra.Context) -> bool | None: ...

# after_invoke : reçoit le contexte du groupe racine
# Toujours appelé (bloc finally)
def my_after_hook(ctx: click_extra.Context) -> None: ...
```

### Stockage

Les hooks sont stockés dans `ctx.meta` après la création du contexte, pour qu'ils soient
accessibles depuis n'importe quel niveau sans référence directe à `GroupConfig` :

```
ctx.meta["pyclifer.before_invoke"] = before_invoke  # list[Callable]
ctx.meta["pyclifer.after_invoke"]  = after_invoke   # list[Callable]
```

### Blocage par before_invoke

Si un hook `before_invoke` retourne `False` ou lève une exception, l'exécution s'arrête.
Une exception levée par un hook remonte normalement (non interceptée par le framework).

### Ordre d'exécution

`before_invoke` : ordre de déclaration (gauche → droite).
`after_invoke` : ordre de déclaration (gauche → droite), dans un `finally`.

---

## Fichiers à modifier

| Fichier | Changement |
|---------|-----------|
| `src/pyclifer/core/classes.py` | Ajouter `before_invoke` et `after_invoke` dans `GroupConfig` |
| `src/pyclifer/core/decorators.py` | Stocker les hooks dans `ctx.meta` depuis `_patch_make_context` |
| `src/pyclifer/core/mixins/cli.py` | Ajouter `HooksMixin` avec `invoke()` patché |
| `src/pyclifer/core/classes.py` | `PycliferExtraGroup` et `PycliferRichGroup` héritent de `HooksMixin` |
| `tests/core/test_hooks.py` | Nouveaux tests (nouveau fichier) |

---

## Tâche 1 : Créer la branche et écrire les tests échouants

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/middleware-hooks
```

- [ ] **Étape 2 : Créer `tests/core/test_hooks.py`**

```python
"""Tests for before_invoke / after_invoke middleware hooks."""
from unittest.mock import MagicMock, call
from click.testing import CliRunner
from pyclifer import app_group, command, pass_context, Response, returns_response


def make_cli(before=None, after=None):
    @app_group(
        add_version_option=False,
        before_invoke=before or [],
        after_invoke=after or [],
    )
    @pass_context
    def cli(ctx):
        pass

    @cli.command()
    @returns_response
    @pass_context
    def hello(ctx):
        return Response(success=True, message="hello", data={})

    return cli


class TestBeforeInvoke:
    """before_invoke hooks are called before each subcommand."""

    def test_before_hook_is_called(self):
        hook = MagicMock()
        cli = make_cli(before=[hook])
        runner = CliRunner()
        result = runner.invoke(cli, ["hello"])
        assert result.exit_code == 0
        hook.assert_called_once()

    def test_multiple_before_hooks_called_in_order(self):
        calls = []
        cli = make_cli(before=[lambda ctx: calls.append("a"), lambda ctx: calls.append("b")])
        runner = CliRunner()
        runner.invoke(cli, ["hello"])
        assert calls == ["a", "b"]

    def test_before_hook_returning_false_blocks_execution(self):
        executed = []

        def blocker(ctx):
            return False

        @app_group(add_version_option=False, before_invoke=[blocker])
        @pass_context
        def cli(ctx):
            pass

        @cli.command()
        def hello():
            executed.append(True)

        runner = CliRunner()
        runner.invoke(cli, ["hello"])
        assert executed == []

    def test_before_hook_raising_exception_propagates(self):
        def bad_hook(ctx):
            raise RuntimeError("auth failed")

        cli = make_cli(before=[bad_hook])
        runner = CliRunner()
        result = runner.invoke(cli, ["hello"], catch_exceptions=True)
        assert result.exit_code != 0


class TestAfterInvoke:
    """after_invoke hooks are called after each subcommand, even on failure."""

    def test_after_hook_is_called(self):
        hook = MagicMock()
        cli = make_cli(after=[hook])
        runner = CliRunner()
        runner.invoke(cli, ["hello"])
        hook.assert_called_once()

    def test_after_hook_called_even_on_command_failure(self):
        hook = MagicMock()

        @app_group(add_version_option=False, after_invoke=[hook])
        @pass_context
        def cli(ctx):
            pass

        @cli.command()
        def fail():
            raise RuntimeError("boom")

        runner = CliRunner()
        runner.invoke(cli, ["fail"], catch_exceptions=True)
        hook.assert_called_once()

    def test_multiple_after_hooks_called_in_order(self):
        calls = []
        cli = make_cli(after=[lambda ctx: calls.append("x"), lambda ctx: calls.append("y")])
        runner = CliRunner()
        runner.invoke(cli, ["hello"])
        assert calls == ["x", "y"]
```

- [ ] **Étape 3 : Confirmer l'échec**

```bash
python -m pytest tests/core/test_hooks.py -v
```

Attendu : `ERROR` — `before_invoke` n'est pas un paramètre reconnu par `GroupConfig`.

---

## Tâche 2 : Ajouter `before_invoke` et `after_invoke` dans `GroupConfig`

**Fichier :** `src/pyclifer/core/classes.py`

- [ ] **Étape 1 : Importer `Callable` si pas déjà présent**

S'assurer que `from collections.abc import Callable` est importé.

- [ ] **Étape 2 : Ajouter les champs dans `GroupConfig`**

Localiser la dataclass `GroupConfig` et ajouter après les champs existants :

```python
    before_invoke: list[Callable] = dataclasses.field(default_factory=list)
    after_invoke: list[Callable] = dataclasses.field(default_factory=list)
```

---

## Tâche 3 : Créer `HooksMixin` dans `cli.py`

**Fichier :** `src/pyclifer/core/mixins/cli.py`

- [ ] **Étape 1 : Ajouter `HooksMixin` en bas du fichier**

```python
class HooksMixin:
    """Mixin that runs before_invoke / after_invoke hooks around subcommand execution.

    Hooks are stored in ctx.meta under 'pyclifer.before_invoke' and
    'pyclifer.after_invoke'. before_invoke hooks returning False block execution.
    after_invoke hooks are always called in a finally block.
    """

    def invoke(self, ctx: Any) -> Any:
        """Run hooks around the parent invoke() call."""
        before_hooks = ctx.meta.get("pyclifer.before_invoke", [])
        after_hooks = ctx.meta.get("pyclifer.after_invoke", [])

        for hook in before_hooks:
            if hook(ctx) is False:
                return None

        try:
            return super().invoke(ctx)
        finally:
            for hook in after_hooks:
                hook(ctx)
```

Ajouter `from typing import Any` si pas déjà présent.

- [ ] **Étape 2 : Exporter `HooksMixin` depuis `mixins/__init__.py`**

```python
from .cli import GlobalOptionsMixin, StoreInMetaMixin, HooksMixin
```

---

## Tâche 4 : Intégrer `HooksMixin` dans les classes de groupe

**Fichier :** `src/pyclifer/core/classes.py`

- [ ] **Étape 1 : Ajouter `HooksMixin` à l'ordre d'héritage**

Respecter l'ordre MRO : mixins avant la classe concrète.

```python
# Avant
class PycliferExtraGroup(HandleResponseMixin, GlobalOptionsMixin, ExtraGroup):

# Après
class PycliferExtraGroup(HandleResponseMixin, GlobalOptionsMixin, HooksMixin, ExtraGroup):
```

```python
# Avant
class PycliferRichGroup(HandleResponseMixin, GlobalOptionsMixin, RichGroup):

# Après
class PycliferRichGroup(HandleResponseMixin, GlobalOptionsMixin, HooksMixin, RichGroup):
```

---

## Tâche 5 : Stocker les hooks dans `ctx.meta` depuis `_patch_make_context`

**Fichier :** `src/pyclifer/core/decorators.py`

- [ ] **Étape 1 : Ajouter le stockage dans le bloc post-call de `custom_make_context`**

Dans `_patch_make_context`, localiser le bloc `# --- post-call ---` → `# Concern 3` :

```python
            # Concern 3 — framework meta injection
            if parent is None:
                ctx.meta.setdefault("pyclifer.unhandled_exception_log_level", level)
                ctx.meta.setdefault("pyclifer.exit_codes_class", exit_codes_cls)
```

Ajouter après :

```python
                ctx.meta.setdefault("pyclifer.before_invoke", self.config.before_invoke)
                ctx.meta.setdefault("pyclifer.after_invoke", self.config.after_invoke)
```

---

## Tâche 6 : Vérification complète

- [ ] **Étape 1 : Tous les tests passent**

```bash
python -m pytest tests/ -v
```

- [ ] **Étape 2 : Couverture de `HooksMixin.invoke()`**

```bash
python -m pytest tests/core/test_hooks.py -v --cov=src/pyclifer/core/mixins --cov-report=term-missing
```

Les deux branches de `if hook(ctx) is False` et le bloc `finally` doivent être couverts.

---

## Tâche 7 : Lint et commit

- [ ] **Étape 1 : Ruff**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

- [ ] **Étape 2 : Mettre à jour `__all__` si `HooksMixin` est exposé publiquement**

Dans `src/pyclifer/__init__.py`, ajouter `"HooksMixin"` dans `__all__`.

- [ ] **Étape 3 : Commit**

```bash
git add src/ tests/core/test_hooks.py
git commit -m "$(cat <<'EOF'
✨ feat(mixins): add before_invoke / after_invoke middleware hooks

- GroupConfig gains before_invoke and after_invoke list fields
- HooksMixin.invoke() runs hooks around subcommand execution
- before_invoke hooks returning False block execution
- after_invoke hooks run in finally — always called even on failure
- Hooks stored in ctx.meta so any layer can access them
EOF
)"
```