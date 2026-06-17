# Mode dry-run global

**Objectif :** Ajouter `--dry-run` comme option globale optionnelle sur `@app_group`.
Quand activé, stocke `True` dans `ctx.meta["pyclifer.dry_run"]`. `BaseInterface` expose
`is_dry_run` pour que les interfaces puissent retourner des résultats simulés sans écrire.

**Cas d'usage cible :**

```python
@app_group(add_dry_run_option=True)
def cli(): ...

# Dans une interface :
class ArticleInterface(BaseInterface):
    def delete(self, article_id: int) -> list[OperationResult]:
        if self.is_dry_run:
            return [OperationResult.dry_run(item=str(article_id), message="Would delete article")]
        # ... suppression réelle
```

```bash
myapp articles delete 42 --dry-run
# → [DRY-RUN] Would delete article (aucune suppression réelle)
```

**Stack :** stdlib uniquement.

---

## Design

### Décision : option globale `is_global=True`

`--dry-run` doit être accessible depuis n'importe quelle sous-commande de la chaîne.
Même pattern que `--verbosity` et `--output-format`.

### Stockage

`ctx.meta["pyclifer.dry_run"]` — booléen. Défaut : `False` quand l'option est absente ou
que `add_dry_run_option=False`.

### `BaseInterface.is_dry_run`

Propriété qui lit `ctx.meta.get("pyclifer.dry_run", False)`. `self.ctx` peut être une
instance de `BaseContext` ou tout objet avec un attribut `meta` (duck typing).

### `OperationResult.dry_run()`

Classmethod qui crée un `OperationResult(success=True, ...)` avec un préfixe `[DRY-RUN]`
dans le message. Le résultat est un succès car aucune erreur ne s'est produite.

```python
@classmethod
def dry_run(cls, item: str, message: str) -> OperationResult:
    return cls(success=True, item=item, message=f"[DRY-RUN] {message}")
```

### Séparation des responsabilités

Le framework fournit l'option et la propriété. La logique de bypass est dans les interfaces
utilisateur — pyclifer ne force rien.

---

## Fichiers à modifier

| Fichier | Changement |
|---------|-----------|
| `src/pyclifer/core/classes.py` | Ajouter `add_dry_run_option: bool = False` dans `GroupConfig` |
| `src/pyclifer/core/decorators.py` | Ajouter `dry_run_option()` ; l'injecter dans `_apply_automatic_options()` |
| `src/pyclifer/core/interfaces/base.py` | Ajouter `is_dry_run` property |
| `src/pyclifer/core/output/responses.py` | Ajouter `OperationResult.dry_run()` classmethod |
| `tests/core/test_dry_run.py` | Nouveaux tests (nouveau fichier) |

---

## Tâche 1 : Créer la branche et écrire les tests échouants

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/dry-run-mode
```

- [ ] **Étape 2 : Créer `tests/core/test_dry_run.py`**

```python
"""Tests for --dry-run global option and BaseInterface.is_dry_run."""
from click.testing import CliRunner
from unittest.mock import MagicMock
from pyclifer import app_group, command, pass_context, returns_response, Response
from pyclifer.core.interfaces.base import BaseInterface
from pyclifer.core.output.responses import OperationResult


def make_dry_run_cli():
    @app_group(add_version_option=False, add_dry_run_option=True)
    @pass_context
    def cli(ctx):
        pass

    @cli.command()
    @returns_response
    @pass_context
    def status(ctx):
        return Response(
            success=True,
            message="dry_run=%s" % ctx.meta.get("pyclifer.dry_run", False),
            data={},
        )

    return cli


class TestDryRunOption:
    """--dry-run stores True in ctx.meta and is accessible from commands."""

    def test_dry_run_false_by_default(self):
        cli = make_dry_run_cli()
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert "dry_run=False" in result.output

    def test_dry_run_true_when_flag_passed(self):
        cli = make_dry_run_cli()
        runner = CliRunner()
        result = runner.invoke(cli, ["--dry-run", "status"])
        assert "dry_run=True" in result.output

    def test_dry_run_not_added_when_disabled(self):
        @app_group(add_version_option=False, add_dry_run_option=False)
        @pass_context
        def cli(ctx):
            pass

        runner = CliRunner()
        result = runner.invoke(cli, ["--dry-run", "--help"], catch_exceptions=False)
        assert result.exit_code != 0 or "--dry-run" not in result.output


class TestBaseInterfaceIsDryRun:
    """BaseInterface.is_dry_run reads from ctx.meta."""

    def test_is_dry_run_false_when_not_set(self):
        ctx = MagicMock()
        ctx.meta = {}
        iface = BaseInterface(ctx)
        assert iface.is_dry_run is False

    def test_is_dry_run_true_when_set(self):
        ctx = MagicMock()
        ctx.meta = {"pyclifer.dry_run": True}
        iface = BaseInterface(ctx)
        assert iface.is_dry_run is True


class TestOperationResultDryRun:
    """OperationResult.dry_run() creates a success result with [DRY-RUN] prefix."""

    def test_dry_run_result_is_success(self):
        result = OperationResult.dry_run(item="42", message="Would delete article")
        assert result.success is True

    def test_dry_run_result_has_prefix(self):
        result = OperationResult.dry_run(item="42", message="Would delete article")
        assert result.message.startswith("[DRY-RUN]")
        assert "Would delete article" in result.message

    def test_dry_run_result_item_is_preserved(self):
        result = OperationResult.dry_run(item="my-resource", message="Would create")
        assert result.item == "my-resource"

    def test_dry_run_result_error_code_is_zero(self):
        result = OperationResult.dry_run(item="x", message="Would do something")
        assert result.error_code == 0
```

- [ ] **Étape 3 : Confirmer l'échec**

```bash
python -m pytest tests/core/test_dry_run.py -v
```

Attendu : `TypeError` — `add_dry_run_option` n'est pas un champ de `GroupConfig`.

---

## Tâche 2 : Ajouter `add_dry_run_option` dans `GroupConfig`

**Fichier :** `src/pyclifer/core/classes.py`

- [ ] **Étape 1 : Ajouter le champ dans `GroupConfig`**

```python
    add_dry_run_option: bool = False
```

---

## Tâche 3 : Ajouter `dry_run_option()` dans `decorators.py`

**Fichier :** `src/pyclifer/core/decorators.py`

- [ ] **Étape 1 : Ajouter la fonction `dry_run_option()`**

Après `output_filter_option()` :

```python
def dry_run_option(
    *param_decls: str,
    is_global: bool = True,
    show_envvar: bool = True,
    **kwargs: Any,
) -> Callable[[Callable], Callable]:
    """Add a --dry-run flag to a command or group.

    When set, stores True in ctx.meta['pyclifer.dry_run']. Commands and
    interfaces can read this flag via BaseInterface.is_dry_run to simulate
    operations without writing state.

    Args:
        *param_decls: Parameter declarations (default: '--dry-run').
        is_global: If True, the option is propagated to all subcommands.
        show_envvar: Show environment variables in the help output.
        **kwargs: Additional arguments passed to the option decorator.

    Returns:
        The decorated function.
    """
    if not param_decls:
        param_decls = ("--dry-run",)

    kwargs.setdefault("is_flag", True)
    kwargs.setdefault("default", False)
    kwargs.setdefault("help", "Simulate operations without writing state.")
    kwargs.setdefault("store_in_meta", True)

    return option(*param_decls, is_global=is_global, show_envvar=show_envvar, **kwargs)
```

- [ ] **Étape 2 : L'injecter dans `_apply_automatic_options()`**

Dans `GroupDecorator._apply_automatic_options()`, ajouter après la gestion de `add_log_file_option` :

```python
        if self.config.add_dry_run_option:
            f = dry_run_option()(f)
```

Le nom de la meta-clé généré par `store_in_meta=True` doit être `pyclifer.dry_run`.
Vérifier que le callback de `StoreInMetaMixin` utilise `pyclifer.<param_name>` comme clé.
Si la clé générée est différente, passer `meta_key="pyclifer.dry_run"` si l'API le supporte,
sinon utiliser un callback explicite.

---

## Tâche 4 : Ajouter `is_dry_run` sur `BaseInterface`

**Fichier :** `src/pyclifer/core/interfaces/base.py`

- [ ] **Étape 1 : Ajouter la propriété**

```python
    @property
    def is_dry_run(self) -> bool:
        """Return True when the --dry-run flag is active.

        Reads from ctx.meta['pyclifer.dry_run']. Defaults to False when
        the option is absent or add_dry_run_option was not set.

        Returns:
            True if dry-run mode is active, False otherwise.
        """
        meta = getattr(self.ctx, "meta", {})
        return bool(meta.get("pyclifer.dry_run", False))
```

---

## Tâche 5 : Ajouter `OperationResult.dry_run()` classmethod

**Fichier :** `src/pyclifer/core/output/responses.py`

- [ ] **Étape 1 : Ajouter après `OperationResult.error()`**

```python
    @classmethod
    def dry_run(cls, item: str, message: str) -> OperationResult:
        """Create a successful dry-run result.

        The message is prefixed with '[DRY-RUN]' to signal that no state
        was actually changed.

        Args:
            item: Human-readable identifier for the simulated operation.
            message: Description of what would have happened.

        Returns:
            A successful OperationResult with a [DRY-RUN] prefix on the message.
        """
        return cls(success=True, item=item, message=f"[DRY-RUN] {message}", error_code=0)
```

---

## Tâche 6 : Vérification complète

- [ ] **Étape 1 : Tous les tests passent**

```bash
python -m pytest tests/ -v
```

- [ ] **Étape 2 : Vérifier la méta-clé générée par `store_in_meta`**

```bash
python -c "
from click.testing import CliRunner
from pyclifer import app_group, pass_context, returns_response, Response

@app_group(add_version_option=False, add_dry_run_option=True)
@pass_context
def cli(ctx): pass

@cli.command()
@pass_context
def check(ctx):
    print('meta:', dict(ctx.meta))

CliRunner().invoke(cli, ['--dry-run', 'check'], catch_exceptions=False)
"
```

Confirmer que `pyclifer.dry_run` est bien la clé dans `ctx.meta`.

---

## Tâche 7 : Lint et commit

- [ ] **Étape 1 : Ruff**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

- [ ] **Étape 2 : Commit**

```bash
git add src/ tests/core/test_dry_run.py
git commit -m "$(cat <<'EOF'
✨ feat(decorators): add --dry-run global option

- GroupConfig.add_dry_run_option injects --dry-run flag (default False)
- dry_run_option() stores result in ctx.meta['pyclifer.dry_run']
- BaseInterface.is_dry_run reads the flag from ctx.meta
- OperationResult.dry_run() creates a success result with [DRY-RUN] prefix
EOF
)"
```