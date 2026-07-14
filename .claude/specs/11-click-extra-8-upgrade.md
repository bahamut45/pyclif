# Mise à jour click-extra 7.20.1 → 8.x

**Objectif :** Lever la contrainte `click-extra>=7.20.1,<8.0.0` vers `>=8.3.0,<9.0.0`. La 8.0.0
supprime le préfixe `Extra` sur plusieurs classes internes (`ExtraGroup` → `Group`,
`ExtraFormatter` → `Formatter`, `ExtraStreamHandler` → `StreamHandler`, `extraBasicConfig` →
`basicConfig`). pyclifer utilise directement ces 4 symboles renommés — tout le reste de l'API
publique consommée par pyclifer est inchangé.

**Vérification préalable (déjà faite manuellement) :** worktree jetable + venv isolé, click-extra
8.3.0 réellement installé, les 4 renommages appliqués → 666 tests passent, 100% coverage,
`ruff check`/`ruff format` clean sur Python 3.13. Ce spec formalise ces mêmes changements avec TDD
et les valide sur 3.10–3.13 via `tox`.

**Cas d'usage cible :** aucun changement de comportement observable pour les utilisateurs de
pyclifer — mise à jour de dépendance transparente.

**Stack :** aucune nouvelle dépendance. Change uniquement la borne de version de `click-extra`
dans `pyproject.toml`.

---

## Design

### Décision 1 — Renommages 1:1, pas d'abstraction de compatibilité

Les 4 symboles renommés sont importés depuis `click_extra`/`click_extra.logging` à un seul
endroit chacun (`classes.py`, `log/formatters.py`, `log/handlers.py`, `log/config.py`). Pas besoin
d'alias de compatibilité ni de détection de version à l'exécution : pyclifer ne supporte qu'une
seule version de click-extra à la fois (bornée dans `pyproject.toml`), donc on renomme
directement, sans branche conditionnelle.

### Décision 2 — Les classes publiques pyclifer gardent leur nom

`RichExtraFormatter`, `RichExtraStreamHandler`, `PycliferExtraGroup` ne changent pas de nom — seule
la classe de base importée de click-extra change. Aucun impact sur l'API publique de pyclifer, pas
de bump majeur de version nécessaire pour ce changement.

### Décision 3 — Vérifier `version_option` et `ConfigOption` restent inchangés

Deux points identifiés comme potentiellement risqués lors de l'audit mais confirmés sans risque :
- `click_extra.version_option(**version_kw)` où `version_kw` peut contenir `version=...` — reste
  valide grâce au compat shim ajouté par click-extra en 8.1.0 (`version` accepté en positionnel ou
  en kwarg, transféré vers `fields={"version": ...}` en interne).
- `from click_extra.config import ConfigOption` — le module a été réorganisé en package
  (`click_extra.config.option`), mais `ConfigOption` reste ré-exporté depuis `click_extra.config`.

Pas de changement de code requis pour ces deux points — seulement une assertion de test qui les
couvre déjà (`test_decorators.py`, `test_classes.py`) doit continuer à passer telle quelle.

### Décision 4 — Étendre la matrice `tox` avant de fusionner

L'audit manuel n'a couvert que Python 3.13. Avant de fusionner, `tox` doit passer sur 3.10, 3.11,
3.12 et 3.13 pour confirmer qu'aucune des 4 classes renommées ne se comporte différemment selon la
version d'interpréteur (peu probable, mais c'est la garantie donnée par `tox` dans ce projet).

---

## Fichiers à modifier

| Fichier                                    | Changement                                                  |
|----------------------------------------------|---------------------------------------------------------------|
| `pyproject.toml`                            | `click-extra>=8.3.0,<9.0.0`                                    |
| `src/pyclifer/core/classes.py`              | `click_extra.ExtraGroup` → `click_extra.Group`                |
| `src/pyclifer/core/log/formatters.py`       | `ExtraFormatter` → `Formatter` (import + base class)           |
| `src/pyclifer/core/log/handlers.py`         | `ExtraStreamHandler` → `StreamHandler` (import + base class)   |
| `src/pyclifer/core/log/config.py`           | `extraBasicConfig` → `basicConfig` (import + appel + docstring)|
| `tests/core/log/test_rich_logging.py`       | Cibles `@patch(...)` : `extraBasicConfig` → `basicConfig`      |

---

## Tâche 1 : Créer la branche et bumper la contrainte

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/click-extra-8-upgrade
```

- [ ] **Étape 2 : `pyproject.toml`**

```toml
dependencies = [
    "click-extra>=8.3.0,<9.0.0",
    ...
]
```

- [ ] **Étape 3 : Synchroniser l'environnement**

```bash
uv sync --extra dev,docs
python -c "import click_extra; print(click_extra.__version__)"  # doit afficher 8.3.x ou plus
```

---

## Tâche 2 : Constater l'échec (tests existants cassés par la montée de version)

- [ ] **Étape 1 : Lancer la suite sans toucher au code**

```bash
python -m pytest tests/ -v
```

Attendu : `AttributeError: module 'click_extra' has no attribute 'ExtraGroup'` à la collection
(import de `pyclifer.core.classes`), qui bloque toute la suite.

---

## Tâche 3 : Renommer `ExtraGroup` → `Group`

**Fichier :** `src/pyclifer/core/classes.py`

- [ ] **Étape 1 :**

```python
class PycliferExtraGroup(HandleResponseMixin, GlobalOptionsMixin, click_extra.Group):
```

- [ ] **Étape 2 : Confirmer que la collection avance**

```bash
python -m pytest tests/ -v
```

Attendu : la suite se relance mais échoue maintenant sur `ExtraFormatter`
(`tests/core/log/test_rich_logging.py` ou import de `pyclifer.core.log`).

---

## Tâche 4 : Renommer `ExtraFormatter` → `Formatter`

**Fichier :** `src/pyclifer/core/log/formatters.py`

- [ ] **Étape 1 :**

```python
from click_extra.logging import Formatter


class RichExtraFormatter(Formatter):
    """Enhanced Formatter with Rich text capabilities and TRACE level support.

    Extends click-extra's Formatter to support Rich markup and custom TRACE level
    while preserving a click-extra's colorization system.
    """
```

(Le nom de la classe `RichExtraFormatter` ne change pas — seule la classe de base et les
mentions dans la docstring.)

---

## Tâche 5 : Renommer `ExtraStreamHandler` → `StreamHandler`

**Fichier :** `src/pyclifer/core/log/handlers.py`

- [ ] **Étape 1 :**

```python
from click_extra.logging import StreamHandler


class RichExtraStreamHandler(StreamHandler):
    """Enhanced StreamHandler with Rich support and built-in security filtering.

    Extends click-extra's StreamHandler to use Rich for beautiful logging
    while maintaining compatibility with click.echo() and color support.
    Automatically includes SecretsMasker for sensitive data protection.
    """
```

---

## Tâche 6 : Renommer `extraBasicConfig` → `basicConfig`

**Fichier :** `src/pyclifer/core/log/config.py`

- [ ] **Étape 1 : Import**

```python
from click_extra.logging import basicConfig
```

- [ ] **Étape 2 : Appel** (dans `configure_rich_logging`)

```python
        basicConfig(
            stream_handler_class=RichExtraStreamHandler,
            formatter_class=RichExtraFormatter,
            force=True,
        )
```

- [ ] **Étape 3 : Docstring** — remplacer la mention "Global configuration via extraBasicConfig"
  par "Global configuration via basicConfig".

---

## Tâche 7 : Mettre à jour les cibles de mock dans les tests

**Fichier :** `tests/core/log/test_rich_logging.py`

- [ ] **Étape 1 :** remplacer les 5 occurrences de
  `@patch("pyclifer.core.log.config.extraBasicConfig")` /
  `patch("pyclifer.core.log.config.extraBasicConfig")` par
  `pyclifer.core.log.config.basicConfig`.
- [ ] **Étape 2 :** mettre à jour les 2 commentaires mentionnant `extraBasicConfig` dans les
  docstrings de test (`test_configure_rich_logging_preserves_file_handler_already_present` et
  environs) pour cohérence — pas obligatoire fonctionnellement mais évite une référence morte.

- [ ] **Étape 3 : Confirmer le succès**

```bash
python -m pytest tests/ -v
```

Attendu : tous les tests passent.

---

## Tâche 8 : Vérification complète multi-version

- [ ] **Étape 1 : Suite complète + coverage**

```bash
python -m pytest tests/ -v
```

Attendu : 100% coverage maintenu (déjà le cas avant ce changement).

- [ ] **Étape 2 : Lint**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

- [ ] **Étape 3 : Matrice complète 3.10–3.13**

```bash
tox
```

Si un échec apparaît sur une version précise de Python, l'investiguer avant de continuer — ce
spec ne couvre que les 4 renommages identifiés ; un échec ailleurs indique une régression
non prévue de click-extra 8.x à traiter au cas par cas.

- [ ] **Étape 4 : Documentation**

```bash
mkdocs build --strict
```

Aucun contenu de `docs/` ne référence les noms `Extra*`/`extraBasicConfig` de click-extra
directement (vérifié par recherche) — pas de changement de documentation attendu au-delà de cette
vérification.

---

## Tâche 9 : Commit

```bash
git add pyproject.toml src/ tests/ .claude/specs/11-click-extra-8-upgrade.md
git commit -m "$(cat <<'EOF'
♻️ refactor(deps): upgrade click-extra to 8.x

- click-extra 8.0.0 drops the Extra prefix from several internal classes;
  pyclifer imports 4 of them directly (ExtraGroup, ExtraFormatter,
  ExtraStreamHandler, extraBasicConfig) — renamed to their 8.x equivalents
- pyclifer's own public classes (RichExtraFormatter, RichExtraStreamHandler,
  PycliferExtraGroup) keep their names; only their imported base class changes
- version_option and ConfigOption usage confirmed unaffected by the bump
- Bump dependency floor to click-extra>=8.3.0,<9.0.0
EOF
)"
```

Obtenir la validation utilisateur avant de fusionner dans `main`, puis supprimer la branche.