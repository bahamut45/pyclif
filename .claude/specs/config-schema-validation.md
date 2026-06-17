# Validation du schéma de configuration via Pydantic

**Objectif :** Permettre à `@app_group(config_schema=MyConfig)` de valider
automatiquement la configuration chargée (TOML/YAML/JSON) contre un modèle Pydantic
`BaseModel`. Erreur claire au démarrage si la config est invalide. Config validée
accessible dans `ctx.meta["pyclifer.config"]`.

**Cas d'usage cible :**

```python
from pyclifer import BaseModel, app_group

class AppConfig(BaseModel):
    api_url: str
    timeout: int = 30
    debug: bool = False

@app_group(config_schema=AppConfig)
def cli(): ...
```

```bash
myapp --config ./config.toml hello
# Si config.toml contient timeout: "not-an-int" :
# Error: config validation failed — timeout: Input should be a valid integer
```

**Stack :** Pydantic (déjà dépendance via `BaseModel`), stdlib.

---

## Design

### Décision : validation dans `_patch_make_context` post-call

`CustomConfigOption` charge la config et injecte les valeurs dans les paramètres Click
via le mécanisme de click_extra. Les valeurs sont disponibles dans `ctx.params` après
`original_make_context()`. C'est là qu'on peut construire le modèle Pydantic.

### Source des données pour la validation

La config chargée par `CustomConfigOption` est fusionnée dans `ctx.params`. On ne peut
pas accéder au dict brut TOML/YAML directement sans modifier click_extra. On construit
donc le modèle Pydantic à partir de `ctx.params` filtré aux champs du schéma.

### Stockage

```
ctx.meta["pyclifer.config"]  →  instance validée du modèle Pydantic
```

### Erreur de validation

`pydantic.ValidationError` → transformée en `click.UsageError` avec le message formaté.
Cela déclenche l'affichage standard Click "Error: <message>" et sort avec code 2.

### `config_schema` optionnel

`config_schema: type[BaseModel] | None = None` dans `GroupConfig`. Si `None`,
aucune validation. Aucun changement de comportement pour les apps existantes.

---

## Fichiers à modifier

| Fichier | Changement |
|---------|-----------|
| `src/pyclifer/core/classes.py` | Ajouter `config_schema` dans `GroupConfig` |
| `src/pyclifer/core/decorators.py` | Valider dans `_patch_make_context` post-call |
| `tests/core/test_config_schema.py` | Nouveaux tests (nouveau fichier) |

---

## Tâche 1 : Créer la branche et écrire les tests échouants

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/config-schema-validation
```

- [ ] **Étape 2 : Créer `tests/core/test_config_schema.py`**

```python
"""Tests for config_schema validation on @app_group."""
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from pyclifer import app_group, BaseModel, pass_context, returns_response, Response


class AppConfig(BaseModel):
    api_url: str
    timeout: int = 30
    debug: bool = False


def make_cli_with_schema(schema=AppConfig):
    @app_group(
        add_version_option=False,
        config_schema=schema,
    )
    @pass_context
    def cli(ctx):
        pass

    @cli.command()
    @pass_context
    def status(ctx):
        config = ctx.meta.get("pyclifer.config")
        if config:
            print(f"api_url={config.api_url}")
            print(f"timeout={config.timeout}")
        else:
            print("no config")

    return cli


def write_toml(content: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False)
    f.write(content)
    f.flush()
    return f.name


class TestConfigSchemaValid:
    """Valid config is loaded and accessible via ctx.meta['pyclifer.config']."""

    def test_valid_config_populates_meta(self):
        config_file = write_toml('[myapp]\napi_url = "https://api.example.com"\ntimeout = 60\n')
        try:
            cli = make_cli_with_schema()
            runner = CliRunner()
            result = runner.invoke(cli, ["--config", config_file, "status"])
            assert result.exit_code == 0, result.output
            assert "api_url=https://api.example.com" in result.output
            assert "timeout=60" in result.output
        finally:
            os.unlink(config_file)

    def test_default_values_applied_when_fields_absent(self):
        config_file = write_toml('[myapp]\napi_url = "https://api.example.com"\n')
        try:
            cli = make_cli_with_schema()
            runner = CliRunner()
            result = runner.invoke(cli, ["--config", config_file, "status"])
            assert result.exit_code == 0
            assert "timeout=30" in result.output  # Pydantic default
        finally:
            os.unlink(config_file)

    def test_no_schema_no_validation(self):
        cli = make_cli_with_schema(schema=None)
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert "no config" in result.output
        assert result.exit_code == 0


class TestConfigSchemaInvalid:
    """Invalid config triggers a clear UsageError with field details."""

    def test_invalid_type_triggers_usage_error(self):
        config_file = write_toml('[myapp]\napi_url = "https://api.example.com"\ntimeout = "not-an-int"\n')
        try:
            cli = make_cli_with_schema()
            runner = CliRunner()
            result = runner.invoke(cli, ["--config", config_file, "status"])
            assert result.exit_code == 2
            assert "config validation failed" in result.output.lower() or \
                   "timeout" in result.output
        finally:
            os.unlink(config_file)

    def test_missing_required_field_triggers_usage_error(self):
        config_file = write_toml('[myapp]\ntimeout = 60\n')
        try:
            cli = make_cli_with_schema()
            runner = CliRunner()
            result = runner.invoke(cli, ["--config", config_file, "status"])
            assert result.exit_code == 2
            assert "api_url" in result.output or "config validation failed" in result.output.lower()
        finally:
            os.unlink(config_file)
```

- [ ] **Étape 3 : Confirmer l'échec**

```bash
python -m pytest tests/core/test_config_schema.py -v
```

Attendu : `TypeError` — `config_schema` n'est pas un champ de `GroupConfig`.

---

## Tâche 2 : Ajouter `config_schema` dans `GroupConfig`

**Fichier :** `src/pyclifer/core/classes.py`

- [ ] **Étape 1 : Ajouter l'import conditionnel de `BaseModel`**

En tête du fichier, ajouter :

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyclifer.core.models import BaseModel as PycliferBaseModel
```

- [ ] **Étape 2 : Ajouter le champ dans `GroupConfig`**

```python
    config_schema: type | None = None
```

Note : `type[PycliferBaseModel] | None` est préférable, mais `type | None` évite le
import circulaire au runtime. Le TYPE_CHECKING guard gère l'IDE.

---

## Tâche 3 : Ajouter la validation dans `_patch_make_context`

**Fichier :** `src/pyclifer/core/decorators.py`

- [ ] **Étape 1 : Ajouter le concern 6 dans `custom_make_context`**

Dans `_patch_make_context`, après le bloc `# Concern 5` (context_factory), ajouter :

```python
            # Concern 6 — config schema validation
            # Validate ctx.params against config_schema (Pydantic BaseModel subclass).
            # Runs only at the root context, after all config files are loaded.
            if (
                parent is None
                and self.config.config_schema is not None
                and not ctx.resilient_parsing
            ):
                import pydantic  # noqa: PLC0415 — lazy import, only when schema is set
                schema_fields = set(self.config.config_schema.model_fields.keys())
                config_data = {
                    k: v for k, v in ctx.params.items()
                    if k in schema_fields and v is not None
                }
                try:
                    validated = self.config.config_schema.model_validate(config_data)
                    ctx.meta["pyclifer.config"] = validated
                except pydantic.ValidationError as exc:
                    from click_extra import UsageError  # noqa: PLC0415
                    errors = "; ".join(
                        f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}"
                        for e in exc.errors()
                    )
                    raise UsageError(f"Config validation failed — {errors}") from exc
```

---

## Tâche 4 : Vérification complète

- [ ] **Étape 1 : Tous les tests passent**

```bash
python -m pytest tests/ -v
```

- [ ] **Étape 2 : Test avec un fichier TOML réel**

Créer `test_cfg.toml` :
```toml
[myapp]
api_url = "https://api.example.com"
timeout = 90
```

```bash
python -c "
from click.testing import CliRunner
from pyclifer import app_group, BaseModel, pass_context

class AppConfig(BaseModel):
    api_url: str
    timeout: int = 30

@app_group(add_version_option=False, config_schema=AppConfig)
@pass_context
def cli(ctx): pass

@cli.command()
@pass_context
def info(ctx):
    cfg = ctx.meta.get('pyclifer.config')
    print('api_url:', cfg.api_url if cfg else 'none')
    print('timeout:', cfg.timeout if cfg else 'none')

from click.testing import CliRunner
r = CliRunner().invoke(cli, ['--config', 'test_cfg.toml', 'info'])
print(r.output)
"
```

- [ ] **Étape 3 : Supprimer `test_cfg.toml`**

```bash
rm -f test_cfg.toml
```

---

## Tâche 5 : Lint et commit

- [ ] **Étape 1 : Ruff**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

- [ ] **Étape 2 : Commit**

```bash
git add src/ tests/core/test_config_schema.py
git commit -m "$(cat <<'EOF'
✨ feat(decorators): add config_schema validation on @app_group

- GroupConfig.config_schema accepts a pyclifer BaseModel subclass
- Validated config instance stored in ctx.meta['pyclifer.config']
- pydantic.ValidationError converted to click.UsageError with field details
- Validation runs post make_context, skipped during resilient_parsing (help)
EOF
)"
```