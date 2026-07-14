# Configuration interactive chiffrée

**Issue GitHub :** [#8 — Interactive encrypted configuration management](https://github.com/bahamut45/pyclifer/issues/8)

**Objectif :** Porter (et sécuriser correctement) le système de configuration interactif de
`ra-tools` : au premier lancement ou quand une section manque, l'utilisateur est prompté pour
chaque valeur ; les champs marqués secrets sont chiffrés au repos via une clé branchable
(`SecretKeyProvider`). Système entièrement séparé de `CustomConfigOption`, qui reste un lecteur
seul de fichiers déjà remplis.

**Cas d'usage cible :**

```python
from pyclifer import (
    app_group, pass_cli_context,
    SecureConfiguration, Property, PasswordProperty, UrlProperty, BoolProperty,
    LocalFileKeyProvider,
)


class MyConfig(SecureConfiguration, key_provider=LocalFileKeyProvider):
    api_url = UrlProperty(label="API URL")
    ssh_password = PasswordProperty(label="SSH password")
    verbose = BoolProperty(label="Verbose by default", default=False)


@app_group(secure_config_schema=MyConfig)
@pass_cli_context
def cli(ctx): ...


@cli.command()
@pass_cli_context
def connect(ctx):
    config = ctx.meta["pyclifer.secure_config"]  # MyConfig instance, prompted/decrypted
    ssh_connect(config.api_url, password=config.ssh_password)
```

```bash
myapp connect
# Premier lancement — champs manquants :
# API URL: https://host.example
# SSH password: ********
# (valeurs stockées dans ~/.config/myapp/secrets.toml, ssh_password chiffré)

myapp connect
# Lancements suivants — aucun prompt, valeurs relues et déchiffrées
```

**Stack :** `cryptography` (Fernet), `tomlkit` (lecture/écriture TOML round-trip) — nouvelles
dépendances, regroupées dans un extra optionnel `pyclifer[secure]` pour ne pas alourdir
l'installation de base des projets qui n'utilisent pas cette fonctionnalité.

---

## Design

### Décision 1 — Coexistence avec `CustomConfigOption` : systèmes entièrement séparés

`CustomConfigOption` reste inchangé : lecture seule d'un fichier déjà rempli (TOML/YAML/JSON/env),
piloté par `--config`. Le nouveau système écrit lui-même son fichier suite au prompt interactif —
mélanger les deux complexifierait la cascade de résolution de `CustomConfigOption` (CLI → env →
fichier → défauts) sans bénéfice, puisque les besoins sont disjoints (une source est en lecture
seule, l'autre lit-ET-écrit). Fichier dédié : `secrets.toml`, situé dans le même répertoire que
`click_extra.get_app_dir(cli_name)` déjà utilisé par `CustomConfigOption` — cohérence des chemins,
mais fichier distinct (`secrets.toml` vs. la config générale de l'utilisateur).

### Décision 2 — Format de fichier : TOML via `tomlkit`, pas `configparser`

`ra-tools` utilisait `.cfg`/`configparser`. On migre vers TOML pour cohérence avec le reste de
pyclifer (`CustomConfigOption` supporte déjà TOML). `tomlkit` plutôt que `tomllib`/`tomli` : il
faut aussi **écrire** le fichier après le prompt initial, et `tomlkit` préserve la structure/les
commentaires lors de la réécriture partielle (utile si un utilisateur édite le fichier à la main
entre deux lancements).

### Décision 3 — Test du wizard interactif : `pyclifer.testing.invoke()` couvre déjà le besoin

`invoke(cli, args, input="valeur1\nvaleur2\n")` (voir `src/pyclifer/testing.py`) accepte déjà une
chaîne d'entrée simulant les réponses aux prompts — aucun nouveau harnais n'est nécessaire. Le
premier test du wizard sert de preuve et de documentation d'usage.

### Décision 4 — `__init_subclass__` plutôt qu'une métaclasse dédiée

L'issue propose un équivalent à `ConfigurationMeta`/`BaseConfiguration` de ra-tools (une
métaclasse). On préfère `SecureConfiguration.__init_subclass__(cls, key_provider=..., path=...)` :
même résultat (collecter les `Property` déclarées en classe, configurer le provider et le chemin
par sous-classe) sans introduire de métaclasse — évite tout conflit si un projet fait un jour
hériter `SecureConfiguration` d'une autre classe à métaclasse (`pydantic.BaseModel`, ABC, etc.).

### Décision 5 — Chiffrement au niveau schéma, pas par propriété

Comme proposé dans l'issue : une seule clé protège tous les secrets d'une installation, configurée
une fois via `key_provider` sur la classe. `PasswordProperty` ne fait que *marquer* un champ comme
secret ; le chiffrement effectif est appliqué par `SecureConfiguration.load()`/`.save()` au moment
de lire/écrire le fichier, pas par la propriété elle-même.

### Décision 6 — Ne pas reproduire la faille de dérivation de clé de `ra-tools`

Point critique relevé dans l'issue : `encrypted_tools.py` dérive la clé Fernet du **nom du champ**
avec un sel statique — n'importe qui lisant le code source peut recalculer la clé. `LocalFileKeyProvider`
génère une clé aléatoire (`Fernet.generate_key()`) **une seule fois**, stockée dans un fichier
séparé du fichier de config (`.secret.key`), jamais dérivée d'une donnée publique.

**Détail de sécurité sur l'écriture initiale** (au-delà du snippet illustratif de l'issue) : la
création du fichier de clé doit utiliser `os.O_CREAT | os.O_EXCL | os.O_WRONLY` (pas seulement
`O_CREAT | O_WRONLY`) pour la toute première écriture — `O_EXCL` fait échouer l'appel si le fichier
existe déjà, fermant la fenêtre de course TOCTOU entre "vérifier l'absence du fichier" et "le
créer". Les lectures suivantes utilisent un `open()` classique.

### Décision 7 — Dépendances optionnelles, import paresseux

`cryptography` et `tomlkit` vont dans `[project.optional-dependencies] secure = [...]`, pas dans
`dependencies` de base. `src/pyclifer/core/secrets.py` importe ces paquets normalement (le module
n'est chargé que si l'utilisateur importe `pyclifer.core.secrets` ou utilise
`secure_config_schema`) ; l'export public dans `pyclifer/__init__.py` suit le même pattern que
`testing.py` : un `try/except ImportError` autour de l'import, avec un message clair si l'extra
n'est pas installé.

---

## Fichiers à modifier

| Fichier                                  | Changement                                                                 |
|-------------------------------------------|-----------------------------------------------------------------------------|
| `pyproject.toml`                          | Nouvel extra `secure = ["cryptography>=42.0", "tomlkit>=0.13"]`             |
| `src/pyclifer/core/secrets.py` (nouveau)  | `Property` + sous-classes, `SecretKeyProvider` + implémentations, `SecureConfiguration` |
| `src/pyclifer/core/classes.py`            | `GroupConfig.secure_config_schema` field                                   |
| `src/pyclifer/core/decorators.py`         | Chargement dans `GroupDecorator._patch_make_context` (nouveau concern)     |
| `src/pyclifer/__init__.py`                | Export conditionnel des symboles `secrets.py`                              |
| `tests/core/test_secrets.py` (nouveau)    | Tests unitaires `Property`, providers, `SecureConfiguration`               |
| `tests/core/test_decorators.py`           | Test d'intégration wizard via `pyclifer.testing.invoke()`                  |
| `docs/api/secrets.md` (nouveau)           | Documentation API                                                          |
| `docs/how-to/secure-configuration.md` (nouveau) | Guide d'usage                                                        |
| `docs/configuration.md`                   | Section "coexistence avec `--config`"                                      |
| `mkdocs.yml`                              | Ajouter les 2 nouvelles pages au `nav`                                      |

---

## Tâche 1 : Créer la branche, ajouter les dépendances

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/interactive-encrypted-configuration
```

- [ ] **Étape 2 : `pyproject.toml`**

```toml
[project.optional-dependencies]
secure = [
    "cryptography>=42.0,<43.0",
    "tomlkit>=0.13,<1.0",
]
```

- [ ] **Étape 3 :**

```bash
uv sync --extra dev,docs,secure
```

---

## Tâche 2 : Tests échouants — `Property` et sous-classes

**Fichier :** `tests/core/test_secrets.py` (nouveau)

```python
import pytest

from pyclifer.core.secrets import (
    BoolProperty,
    EmailProperty,
    IntProperty,
    PasswordProperty,
    Property,
    UrlProperty,
)


class TestProperty:
    """Property declares a single interactively-prompted config field."""

    def test_default_value_used_when_not_required(self):
        prop = Property(label="Name", default="anonymous")
        assert prop.default == "anonymous"

    def test_is_secret_false_by_default(self):
        prop = Property(label="Name")
        assert prop.is_secret is False


class TestPasswordProperty:
    """PasswordProperty marks a field for encryption at rest."""

    def test_is_secret_true(self):
        assert PasswordProperty(label="Password").is_secret is True

    def test_prompt_uses_hide_input(self, monkeypatch):
        captured = {}

        def fake_prompt(text, **kwargs):
            captured.update(kwargs)
            return "s3cr3t"

        monkeypatch.setattr("pyclifer.core.secrets.click_extra.prompt", fake_prompt)

        value = PasswordProperty(label="Password").prompt()

        assert value == "s3cr3t"
        assert captured["hide_input"] is True


class TestUrlProperty:
    """UrlProperty validates the prompted value looks like a URL."""

    def test_rejects_value_without_scheme(self, monkeypatch):
        answers = iter(["not-a-url", "https://example.com"])
        monkeypatch.setattr(
            "pyclifer.core.secrets.click_extra.prompt", lambda *a, **k: next(answers)
        )

        value = UrlProperty(label="API URL").prompt()

        assert value == "https://example.com"


class TestEmailProperty:
    """EmailProperty validates the prompted value contains an '@'."""

    def test_rejects_value_without_at_sign(self, monkeypatch):
        answers = iter(["not-an-email", "user@example.com"])
        monkeypatch.setattr(
            "pyclifer.core.secrets.click_extra.prompt", lambda *a, **k: next(answers)
        )

        value = EmailProperty(label="Email").prompt()

        assert value == "user@example.com"


class TestBoolProperty:
    """BoolProperty prompts via confirm() rather than prompt()."""

    def test_prompt_delegates_to_confirm(self, monkeypatch):
        monkeypatch.setattr("pyclifer.core.secrets.click_extra.confirm", lambda *a, **k: True)
        assert BoolProperty(label="Verbose", default=False).prompt() is True


class TestIntProperty:
    """IntProperty converts the prompted value to int, re-prompting on error."""

    def test_reprompts_until_valid_int(self, monkeypatch):
        answers = iter(["notanumber", "42"])
        monkeypatch.setattr(
            "pyclifer.core.secrets.click_extra.prompt", lambda *a, **k: next(answers)
        )

        assert IntProperty(label="Port").prompt() == 42
```

- [ ] **Confirmer l'échec :**

```bash
python -m pytest tests/core/test_secrets.py -v
```

Attendu : `ModuleNotFoundError: No module named 'pyclifer.core.secrets'`

---

## Tâche 3 : Implémenter `Property` et sous-classes

**Fichier :** `src/pyclifer/core/secrets.py` (nouveau, début du module)

```python
"""Interactive, optionally-encrypted configuration schema for pyclifer projects.

Requires the 'secure' extra (cryptography, tomlkit). Import this module only
when secure_config_schema is used — see pyclifer.__init__ for the guarded
public export.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click_extra

_log = logging.getLogger(__name__)


@dataclass
class Property:
    """A single interactively-prompted configuration field.

    Args:
        label: Prompt text shown to the user.
        default: Value used when the field is optional and left blank.
        required: If True, an empty answer re-prompts instead of falling back to default.
    """

    label: str
    default: Any = None
    required: bool = True
    is_secret: bool = field(default=False, init=False)

    def prompt(self) -> Any:
        """Prompt the user for this field's value.

        Returns:
            The value entered by the user, or default if left blank.
        """
        return click_extra.prompt(self.label, default=self.default, show_default=self.required is False)


@dataclass
class PasswordProperty(Property):
    """A secret field, prompted with hidden input and encrypted at rest."""

    def __post_init__(self) -> None:
        """Mark this property as secret."""
        self.is_secret = True

    def prompt(self) -> Any:
        """Prompt with hidden input so the value is not echoed to the terminal."""
        return click_extra.prompt(
            self.label, default=self.default, hide_input=True, show_default=False
        )


@dataclass
class UrlProperty(Property):
    """A field validated to contain a URL scheme (http:// or https://)."""

    def prompt(self) -> Any:
        """Re-prompt until the value starts with http:// or https://."""
        while True:
            value = click_extra.prompt(self.label, default=self.default)
            if value.startswith(("http://", "https://")):
                return value
            click_extra.echo("Please enter a valid URL (must start with http:// or https://).")


@dataclass
class EmailProperty(Property):
    """A field validated to look like an email address."""

    def prompt(self) -> Any:
        """Re-prompt until the value contains exactly one '@'."""
        while True:
            value = click_extra.prompt(self.label, default=self.default)
            if value.count("@") == 1 and not value.startswith("@") and not value.endswith("@"):
                return value
            click_extra.echo("Please enter a valid email address.")


@dataclass
class BoolProperty(Property):
    """A yes/no field, prompted via confirm()."""

    default: bool = False

    def prompt(self) -> bool:
        """Prompt via click_extra.confirm()."""
        return click_extra.confirm(self.label, default=self.default)


@dataclass
class IntProperty(Property):
    """An integer field, re-prompted until the value parses as int."""

    def prompt(self) -> int:
        """Re-prompt until the value converts to int."""
        while True:
            value = click_extra.prompt(self.label, default=self.default)
            try:
                return int(value)
            except ValueError:
                click_extra.echo("Please enter a whole number.")
```

- [ ] **Confirmer le succès :**

```bash
python -m pytest tests/core/test_secrets.py -v -k "not SecureConfiguration and not KeyProvider"
```

---

## Tâche 4 : Tests échouants — `SecretKeyProvider` et implémentations

**Fichier :** `tests/core/test_secrets.py` (compléter)

```python
import os
import stat

from cryptography.fernet import Fernet

from pyclifer.core.secrets import LocalFileKeyProvider, NoOpKeyProvider


class TestNoOpKeyProvider:
    """NoOpKeyProvider disables encryption explicitly."""

    def test_get_key_returns_none(self):
        assert NoOpKeyProvider().get_key() is None


class TestLocalFileKeyProvider:
    """LocalFileKeyProvider stores a random Fernet key in a 0o600 file."""

    def test_generates_key_on_first_call(self, tmp_path):
        key_path = tmp_path / ".secret.key"
        provider = LocalFileKeyProvider(path=key_path)

        key = provider.get_key()

        assert key_path.exists()
        assert Fernet(key)  # valid Fernet key

    def test_file_permissions_are_owner_only(self, tmp_path):
        key_path = tmp_path / ".secret.key"
        provider = LocalFileKeyProvider(path=key_path)
        provider.get_key()

        mode = stat.S_IMODE(os.stat(key_path).st_mode)
        assert mode == 0o600

    def test_reuses_existing_key_on_subsequent_calls(self, tmp_path):
        key_path = tmp_path / ".secret.key"
        provider = LocalFileKeyProvider(path=key_path)

        first = provider.get_key()
        second = LocalFileKeyProvider(path=key_path).get_key()

        assert first == second
```

- [ ] **Confirmer l'échec :**

```bash
python -m pytest tests/core/test_secrets.py -v -k KeyProvider
```

---

## Tâche 5 : Implémenter `SecretKeyProvider`, `LocalFileKeyProvider`, `NoOpKeyProvider`

**Fichier :** `src/pyclifer/core/secrets.py` (suite du module)

```python
class SecretKeyProvider(ABC):
    """Provides (and manages the lifecycle of) the key used to encrypt PasswordProperty values."""

    @abstractmethod
    def get_key(self) -> bytes | None:
        """Return the Fernet key to use, or None to disable encryption.

        Returns:
            A valid Fernet key, or None to store secrets in plaintext.
        """


class LocalFileKeyProvider(SecretKeyProvider):
    """Default implementation: a random Fernet key generated once, stored on disk.

    The key lives in a file separate from the config file itself, created with
    0o600 permissions. First creation uses O_CREAT | O_EXCL | O_WRONLY to close
    the TOCTOU race window between checking for the file's absence and
    creating it — a symlink or pre-existing file at that path makes the open()
    call fail instead of silently overwriting or following it.
    """

    def __init__(self, path: str | Path) -> None:
        """Initialize the provider with the path to the key file.

        Args:
            path: Where the Fernet key is stored.
        """
        self._path = Path(path)

    def get_key(self) -> bytes:
        """Return the stored key, generating and persisting one on first use.

        Returns:
            The Fernet key bytes.
        """
        if self._path.exists():
            return self._path.read_bytes()

        self._path.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        fd = os.open(str(self._path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            os.write(fd, key)
        finally:
            os.close(fd)
        return key


class NoOpKeyProvider(SecretKeyProvider):
    """Explicit opt-out: PasswordProperty values are stored in plaintext.

    Useful for a project that already manages its secrets elsewhere (external
    vault, env vars) and doesn't want a local key file.
    """

    def get_key(self) -> None:
        """Return None — encryption disabled."""
        return None
```

- [ ] Ajouter en tête de fichier : `import os` et `from cryptography.fernet import Fernet`.
- [ ] **Confirmer le succès :**

```bash
python -m pytest tests/core/test_secrets.py -v -k "not SecureConfiguration"
```

---

## Tâche 6 : Tests échouants — `SecureConfiguration`

**Fichier :** `tests/core/test_secrets.py` (compléter)

```python
from pyclifer.core.secrets import NoOpKeyProvider, SecureConfiguration


class TestSecureConfiguration:
    """SecureConfiguration collects Property fields and drives load()/save()."""

    def test_init_subclass_collects_declared_properties(self, tmp_path):
        class MyConfig(SecureConfiguration, key_provider=NoOpKeyProvider, path=tmp_path / "s.toml"):
            api_url = UrlProperty(label="API URL", default="https://example.com")

        assert "api_url" in MyConfig._properties

    def test_load_prompts_for_missing_fields_and_persists_them(self, tmp_path, monkeypatch):
        answers = iter(["https://example.com"])
        monkeypatch.setattr(
            "pyclifer.core.secrets.click_extra.prompt", lambda *a, **k: next(answers)
        )

        class MyConfig(SecureConfiguration, key_provider=NoOpKeyProvider, path=tmp_path / "s.toml"):
            api_url = UrlProperty(label="API URL")

        config = MyConfig.load()

        assert config.api_url == "https://example.com"
        assert (tmp_path / "s.toml").exists()

    def test_second_load_does_not_reprompt(self, tmp_path, monkeypatch):
        prompts = []
        monkeypatch.setattr(
            "pyclifer.core.secrets.click_extra.prompt",
            lambda *a, **k: prompts.append(1) or "https://example.com",
        )

        class MyConfig(SecureConfiguration, key_provider=NoOpKeyProvider, path=tmp_path / "s.toml"):
            api_url = UrlProperty(label="API URL")

        MyConfig.load()
        MyConfig.load()

        assert len(prompts) == 1

    def test_password_property_is_encrypted_at_rest(self, tmp_path, monkeypatch):
        from pyclifer.core.secrets import LocalFileKeyProvider

        monkeypatch.setattr(
            "pyclifer.core.secrets.click_extra.prompt", lambda *a, **k: "s3cr3t"
        )

        class MyConfig(
            SecureConfiguration,
            key_provider=lambda: LocalFileKeyProvider(tmp_path / ".secret.key"),
            path=tmp_path / "s.toml",
        ):
            ssh_password = PasswordProperty(label="SSH password")

        config = MyConfig.load()

        raw = (tmp_path / "s.toml").read_text()
        assert "s3cr3t" not in raw
        assert config.ssh_password == "s3cr3t"  # decrypted transparently on access

    def test_noop_key_provider_stores_plaintext(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "pyclifer.core.secrets.click_extra.prompt", lambda *a, **k: "s3cr3t"
        )

        class MyConfig(SecureConfiguration, key_provider=NoOpKeyProvider, path=tmp_path / "s.toml"):
            ssh_password = PasswordProperty(label="SSH password")

        config = MyConfig.load()

        raw = (tmp_path / "s.toml").read_text()
        assert "s3cr3t" in raw
        assert config.ssh_password == "s3cr3t"
```

- [ ] **Confirmer l'échec :**

```bash
python -m pytest tests/core/test_secrets.py -v -k SecureConfiguration
```

---

## Tâche 7 : Implémenter `SecureConfiguration`

**Fichier :** `src/pyclifer/core/secrets.py` (fin du module)

```python
import tomlkit


class SecureConfiguration:
    """Base class for a declarative, interactively-prompted, optionally-encrypted schema.

    Subclass with the Property fields you need, then configure the key
    provider and storage path via class keyword arguments:

        class MyConfig(SecureConfiguration, key_provider=LocalFileKeyProvider, path="..."):
            ssh_password = PasswordProperty(label="SSH password")
    """

    _properties: dict[str, Property]
    _key_provider_factory: Any
    _path: Path

    def __init_subclass__(
        cls, key_provider: Any = None, path: str | Path | None = None, **kwargs: Any
    ) -> None:
        """Collect declared Property fields and store schema-level configuration.

        Args:
            key_provider: A SecretKeyProvider subclass, or a zero-arg callable
                returning a SecretKeyProvider instance.
            path: Where the TOML file is read from / written to.
        """
        super().__init_subclass__(**kwargs)
        cls._properties = {
            name: value for name, value in vars(cls).items() if isinstance(value, Property)
        }
        cls._key_provider_factory = key_provider
        cls._path = Path(path) if path is not None else None

    @classmethod
    def _make_key_provider(cls) -> SecretKeyProvider:
        """Instantiate the configured key provider."""
        factory = cls._key_provider_factory
        return factory() if not isinstance(factory, type) else factory()

    @classmethod
    def load(cls) -> SecureConfiguration:
        """Load values from disk, prompting for and persisting any missing field.

        Returns:
            An instance with every declared Property resolved to a value.
        """
        cls._path.parent.mkdir(parents=True, exist_ok=True)
        doc = tomlkit.parse(cls._path.read_text()) if cls._path.exists() else tomlkit.document()

        key_provider = cls._make_key_provider()
        key = key_provider.get_key()
        fernet = Fernet(key) if key is not None else None

        instance = cls()
        dirty = False
        for name, prop in cls._properties.items():
            if name in doc:
                raw = doc[name]
                value = fernet.decrypt(raw.encode()).decode() if prop.is_secret and fernet else raw
            else:
                value = prop.prompt()
                doc[name] = fernet.encrypt(str(value).encode()).decode() if prop.is_secret and fernet else value
                dirty = True
            setattr(instance, name, value)

        if dirty:
            cls._path.write_text(tomlkit.dumps(doc))

        return instance
```

- [ ] **Confirmer le succès :**

```bash
python -m pytest tests/core/test_secrets.py -v
```

---

## Tâche 8 : Wiring — `GroupConfig`, `decorators.py`, export public

- [ ] **Étape 1 : `src/pyclifer/core/classes.py`**

```python
    # Secure interactive configuration
    secure_config_schema: type[Any] | None = None  # type[SecureConfiguration], Any to avoid a hard import
```

- [ ] **Étape 2 : `src/pyclifer/core/decorators.py`** — dans `_patch_make_context`, nouveau concern
  après le concern 5 (context_factory), exécuté seulement `parent is None` et hors
  `resilient_parsing` :

```python
            # Concern 6 — secure_config_schema: load (and possibly prompt) once at root.
            if parent is None and self.config.secure_config_schema is not None and not ctx.resilient_parsing:
                ctx.meta["pyclifer.secure_config"] = self.config.secure_config_schema.load()
```

- [ ] **Étape 3 : `src/pyclifer/__init__.py`** — export conditionnel, même pattern que
  `testing.py` :

```python
try:
    from .core.secrets import (
        BoolProperty,
        EmailProperty,
        IntProperty,
        LocalFileKeyProvider,
        NoOpKeyProvider,
        PasswordProperty,
        Property,
        SecretKeyProvider,
        SecureConfiguration,
        UrlProperty,
    )

    __all__ += [
        "BoolProperty", "EmailProperty", "IntProperty", "LocalFileKeyProvider",
        "NoOpKeyProvider", "PasswordProperty", "Property", "SecretKeyProvider",
        "SecureConfiguration", "UrlProperty",
    ]
except ImportError:  # pragma: no cover — 'secure' extra not installed
    pass
```

---

## Tâche 9 : Test d'intégration — wizard bout-en-bout

**Fichier :** `tests/core/test_decorators.py`

- [ ] Écrire un test avec `@app_group(secure_config_schema=MyConfig)` + une commande lisant
  `ctx.meta["pyclifer.secure_config"]`, invoquée via `pyclifer.testing.invoke(cli, [...], input="https://example.com\n")` —
  vérifier que le premier appel prompte et que `ctx.meta["pyclifer.secure_config"].api_url` est
  bien peuplé.

```bash
python -m pytest tests/core/test_decorators.py -v -k secure_config
```

---

## Tâche 10 : Vérification complète

```bash
python -m pytest tests/ -v
ruff check src/ tests/
ruff format src/ tests/
tox  # confirme la compatibilité 3.10–3.13, notamment tomlkit/cryptography
```

---

## Tâche 11 : Documentation

- [ ] **`docs/api/secrets.md`** (nouveau) — documenter `Property` et sous-classes,
  `SecretKeyProvider`/`LocalFileKeyProvider`/`NoOpKeyProvider`, `SecureConfiguration`.
- [ ] **`docs/how-to/secure-configuration.md`** (nouveau) — reprendre l'exemple du "Cas d'usage
  cible", expliquer l'installation de l'extra (`pip install pyclifer[secure]`), le choix du
  provider, et la mise en garde sur la faille de `ra-tools` évitée (Décision 6).
- [ ] **`docs/configuration.md`** — section "Configuration interactive chiffrée vs. `--config`"
  expliquant la séparation des deux systèmes (Décision 1).
- [ ] **`mkdocs.yml`** — ajouter les 2 nouvelles pages au `nav`.
- [ ] **Étape finale :**

```bash
mkdocs build --strict
```

---

## Tâche 12 : Commit

```bash
git add pyproject.toml src/ tests/ docs/ mkdocs.yml .claude/specs/10-interactive-encrypted-configuration.md
git commit -m "$(cat <<'EOF'
✨ feat(secrets): add interactive encrypted configuration management

- Property/PasswordProperty/UrlProperty/EmailProperty/BoolProperty/IntProperty
  declare interactively-prompted config fields
- SecretKeyProvider (LocalFileKeyProvider, NoOpKeyProvider) pluggable key
  lifecycle — random key in a separate 0o600 file, not derived from the
  field name like ra-tools' encrypted_tools.py (recomputable from public source)
- SecureConfiguration.load() prompts once for missing fields, persists to a
  TOML file separate from CustomConfigOption's read-only cascade
- @app_group(secure_config_schema=...) exposes the loaded instance via
  ctx.meta["pyclifer.secure_config"]
- cryptography/tomlkit gated behind the optional 'secure' extra
- Closes #8
EOF
)"
```

Fusionner dans `main` après validation utilisateur, puis supprimer la branche.