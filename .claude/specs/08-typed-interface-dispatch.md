# Dispatch typé sur `BaseInterface.respond()`

**Objectif :** Éliminer la string `"method_name"` dans `interface.respond("list", ...)`.
Accepter directement un callable : `interface.respond(interface.list, ...)`. Ajouter un
décorateur `@with_renderer_class(MyRenderer)` pour attacher le renderer directement
sur la méthode — plus besoin du dict `renderers` de classe.

**Avant / Après :**

```python
# Avant — fragile, pas de complétion IDE
return self.respond("list", page=page, limit=limit)

# Après — typé, refactorable, complétion IDE
return self.respond(self.list, page=page, limit=limit)

# Avec décorateur — renderer colocalisé avec la méthode
class ArticleInterface(BaseInterface):
    @with_renderer_class(ArticleListRenderer)
    def list(self) -> list[OperationResult]: ...
```

**Stack :** stdlib uniquement. Rétrocompatible avec la signature string existante.

---

## Design

### Note de conception : nommage du décorateur

Inspiré de `renderer_classes` (Django REST Framework — content negotiation multi-format).
Adapté en singulier ici car `BaseRenderer` est déjà la source unique de vérité pour
*tous* les formats de sortie d'une méthode (`table()`, `rich()`, `serialize()`, `text()`,
`raw()` — voir `core/output/renderer.py`). Une méthode d'interface n'a donc jamais besoin
de plus d'un renderer ; le singulier est correct.

Le décorateur n'est volontairement **pas** nommé `renderer_class` (qui serait le miroir
exact de l'attribut de fallback existant `self.renderer_class`). Dans un corps de classe
Python, une assignation `renderer_class = MyRenderer` lie ce nom dans l'espace de noms
local de la classe en cours de construction. Si cette ligne précède un usage
`@renderer_class(...)` plus bas dans le même corps de classe, la résolution du nom du
décorateur retomberait sur la classe renderer assignée plus haut au lieu de la fonction
décorateur importée — `TypeError` à la définition de la classe, dépendant de l'ordre des
lignes. `BaseInterface` autorise justement le mélange du dict `renderers`, du fallback
`renderer_class` et du décorateur par méthode dans une même classe, donc cette collision
serait réelle en usage normal. D'où `with_renderer_class` : distinct de l'attribut
existant, aucune dépendance à l'ordre de déclaration.

Attribut interne posé sur la méthode : `_pyclifer_renderer_class` (aligné sur le nom
du décorateur).

### Priorité de résolution du renderer

1. Décorateur `@with_renderer_class` sur la méthode (pose `_pyclifer_renderer_class`)
2. Dict `self.renderers` (comportement actuel)
3. Attribut de classe `self.renderer_class` (fallback actuel)

### `respond()` avec callable

Quand un callable est passé :
- Extraire `__name__` pour la résolution du renderer via `renderers`
- Détecter `_pyclifer_renderer_class` sur le callable avant le dict
- Appeler le callable directement (il est déjà lié si `self.method` est passé)

### Rétrocompatibilité

La signature `respond("method_name", *args, **kwargs)` continue de fonctionner à l'identique.
Aucune breaking change.

### Type hints

```python
def respond(
    self,
    method_or_name: str | Callable[..., list[OperationResult]],
    *args: object,
    **kwargs: object,
) -> Response:
```

### `@with_renderer_class` décorateur

Fonction simple qui pose un attribut sur la méthode :

```python
def with_renderer_class(
    renderer: type[BaseRenderer],
) -> Callable[[_F], _F]:
    def decorator(f: _F) -> _F:
        f._pyclifer_renderer_class = renderer
        return f
    return decorator
```

---

## Fichiers à modifier

| Fichier | Changement |
|---------|-----------|
| `src/pyclifer/core/interfaces/base.py` | Modifier `respond()`, ajouter `with_renderer_class` |
| `src/pyclifer/__init__.py` | Exporter `with_renderer_class` dans `__all__` |
| `tests/core/interfaces/test_base.py` | Nouveaux tests (nouveau fichier ou extension) |

---

## Tâche 1 : Créer la branche et écrire les tests échouants

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/typed-interface-dispatch
```

- [ ] **Étape 2 : Créer `tests/core/interfaces/test_base.py`**

```python
"""Tests for BaseInterface.respond() with callable dispatch and @with_renderer_class."""
import pytest
from unittest.mock import MagicMock
from pyclifer.core.interfaces.base import BaseInterface, with_renderer_class
from pyclifer.core.output.renderer import BaseRenderer
from pyclifer.core.output.responses import OperationResult


class MyRenderer(BaseRenderer):
    fields = ["name"]
    columns = ["name"]
    success_message = "Done."


class AltRenderer(BaseRenderer):
    fields = ["id"]
    columns = ["id"]
    success_message = "Alt done."


class MyInterface(BaseInterface):
    renderers = {"fetch": MyRenderer}
    renderer_class = MyRenderer

    def fetch(self, item_id: int) -> list[OperationResult]:
        return [OperationResult(success=True, item=str(item_id), data={"name": "Alice"})]

    def create(self, name: str) -> list[OperationResult]:
        return [OperationResult(success=True, item=name, data={"name": name})]

    @with_renderer_class(AltRenderer)
    def search(self, query: str) -> list[OperationResult]:
        return [OperationResult(success=True, item=query, data={"id": "x"})]


class TestRespondWithString:
    """Legacy string dispatch — must remain fully backward compatible."""

    def test_respond_with_string_calls_method(self):
        iface = MyInterface(ctx=MagicMock())
        response = iface.respond("fetch", 42)
        assert response.success is True
        assert response.data["results"][0].item == "42"

    def test_respond_with_string_uses_renderers_dict(self):
        iface = MyInterface(ctx=MagicMock())
        response = iface.respond("fetch", 42)
        assert isinstance(response.renderer, MyRenderer)

    def test_respond_with_string_unknown_method_raises(self):
        iface = MyInterface(ctx=MagicMock())
        with pytest.raises(AttributeError):
            iface.respond("nonexistent")


class TestRespondWithCallable:
    """New callable dispatch — typed, refactorable, IDE-friendly."""

    def test_respond_with_bound_method(self):
        iface = MyInterface(ctx=MagicMock())
        response = iface.respond(iface.fetch, 42)
        assert response.success is True
        assert response.data["results"][0].item == "42"

    def test_respond_with_callable_uses_renderers_dict(self):
        iface = MyInterface(ctx=MagicMock())
        response = iface.respond(iface.fetch, 42)
        assert isinstance(response.renderer, MyRenderer)

    def test_respond_with_callable_fallback_to_renderer_class(self):
        iface = MyInterface(ctx=MagicMock())
        response = iface.respond(iface.create, "Bob")
        assert isinstance(response.renderer, MyRenderer)  # renderer_class fallback

    def test_respond_with_callable_uses_with_renderer_class_decorator(self):
        """Decorator wins even though the class also declares renderer_class = MyRenderer.

        Regression test for the naming-collision rationale: with_renderer_class is a
        distinct name from the renderer_class fallback attribute on the same class, so
        there is no class-body name-shadowing risk to verify here — only that the
        decorator's renderer takes priority over the fallback.
        """
        iface = MyInterface(ctx=MagicMock())
        response = iface.respond(iface.search, "query")
        assert isinstance(response.renderer, AltRenderer)

    def test_respond_with_callable_returns_correct_data(self):
        iface = MyInterface(ctx=MagicMock())
        response = iface.respond(iface.fetch, 99)
        assert response.data["results"][0].data == {"name": "Alice"}


class TestWithRendererClassDecorator:
    """@with_renderer_class attaches a renderer to a method."""

    def test_decorator_sets_pyclifer_renderer_class_attribute(self):
        iface = MyInterface(ctx=MagicMock())
        assert hasattr(iface.search, "_pyclifer_renderer_class")
        assert iface.search._pyclifer_renderer_class is AltRenderer

    def test_decorator_does_not_change_method_behavior(self):
        iface = MyInterface(ctx=MagicMock())
        results = iface.search("hello")
        assert results[0].item == "hello"

    def test_decorator_preserves_function_name(self):
        iface = MyInterface(ctx=MagicMock())
        assert iface.search.__name__ == "search"
```

- [ ] **Étape 3 : Confirmer l'échec**

```bash
python -m pytest tests/core/interfaces/test_base.py -v
```

Attendu : `ImportError: cannot import name 'with_renderer_class' from 'pyclifer.core.interfaces.base'`

---

## Tâche 2 : Modifier `BaseInterface` et ajouter `with_renderer_class`

**Fichier :** `src/pyclifer/core/interfaces/base.py`

- [ ] **Étape 1 : Ajouter les imports manquants en tête du fichier**

```python
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar, TypeVar

_F = TypeVar("_F", bound=Callable)
```

- [ ] **Étape 2 : Ajouter la fonction `with_renderer_class` avant la classe `BaseInterface`**

```python
def with_renderer_class(renderer: type[BaseRenderer]) -> Callable[[_F], _F]:
    """Attach a renderer class to an interface method.

    The renderer takes priority over the class-level renderers dict in respond().
    This co-locates the renderer declaration with the method it belongs to,
    making the renderers dict optional. Named distinctly from the renderer_class
    fallback attribute to avoid class-body name shadowing when both are declared
    on the same BaseInterface subclass.

    Args:
        renderer: The BaseRenderer subclass to use for this method's output.

    Returns:
        A decorator that attaches _pyclifer_renderer_class to the function.
    """

    def decorator(f: _F) -> _F:
        """Attach the renderer to the function."""
        f._pyclifer_renderer_class = renderer  # type: ignore[attr-defined]
        return f

    return decorator
```

- [ ] **Étape 3 : Modifier `respond()` pour accepter un callable**

Remplacer la méthode `respond()` existante par :

```python
    def respond(
        self,
        method_or_name: str | Callable[..., list],
        *args: object,
        **kwargs: object,
    ) -> Response:
        """Call a method and wrap its output in a Response with the right renderer.

        Accepts either a method name string (legacy) or a bound callable (preferred).
        Renderer resolution order:
        1. _pyclifer_renderer_class attribute on the callable (set by @with_renderer_class)
        2. self.renderers dict keyed by method name
        3. self.renderer_class fallback

        Auto-detects whether the method returns a list or a generator and picks
        from_results() vs from_stream() accordingly.

        Args:
            method_or_name: Name of an interface method, or the bound method itself.
            *args: Positional arguments forwarded to the method.
            **kwargs: Keyword arguments forwarded to the method.

        Returns:
            A Response ready for the framework to dispatch to the renderer.

        Raises:
            AttributeError: When method_or_name is a string and no such method exists.
        """
        from pyclifer.core.output.responses import Response  # noqa: PLC0415

        if callable(method_or_name):
            method = method_or_name
            method_name = getattr(method, "__name__", "")
            # Priority 1: renderer attached via @with_renderer_class
            renderer_cls = getattr(method, "_pyclifer_renderer_class", None)
            if renderer_cls is None:
                # Priority 2: renderers dict, then renderer_class fallback
                renderer_cls = self.renderers.get(method_name, self.renderer_class)
        else:
            method_name = method_or_name
            method = getattr(self, method_name)
            renderer_cls = getattr(method, "_pyclifer_renderer_class", None)
            if renderer_cls is None:
                renderer_cls = self.renderers.get(method_name, self.renderer_class)

        renderer = renderer_cls()
        result = method(*args, **kwargs)

        if inspect.isgenerator(result):
            return Response.from_stream(result, renderer=renderer)

        return Response.from_results(
            result,
            success_message=renderer.get_success_message(result),
            failure_message=renderer.get_failure_message(result),
            renderer=renderer,
        )
```

---

## Tâche 3 : Exporter `with_renderer_class` depuis `pyclifer.__init__`

**Fichier :** `src/pyclifer/__init__.py`

- [ ] **Étape 1 : Ajouter l'import**

```python
from .core.interfaces import BaseInterface, with_renderer_class
```

- [ ] **Étape 2 : Ajouter dans `__all__`**

```python
    "with_renderer_class",
```

---

## Tâche 4 : Vérification complète

- [ ] **Étape 1 : Tous les tests passent**

```bash
python -m pytest tests/ -v
```

- [ ] **Étape 2 : Vérifier rétrocompatibilité — les tests existants de BaseInterface passent**

```bash
python -m pytest tests/core/interfaces/ -v
```

---

## Tâche 5 : Documentation

**Fichiers :** `docs/api/interfaces.md`, `docs/examples.md`

- [ ] **Étape 1 : Documenter `@with_renderer_class` et le dispatch callable dans `docs/api/interfaces.md`**

Ajouter, après l'exemple Avant/Après déjà présent en tête de ce spec (réutiliser le
même exemple, ne pas le redupliquer), la section suivante :

```markdown
### `@with_renderer_class` — co-localiser le renderer

Le décorateur `@with_renderer_class` attache un renderer directement sur la méthode,
rendant le dict `renderers` optionnel :

```python
from pyclifer import with_renderer_class

class ArticleInterface(BaseInterface):
    @with_renderer_class(ArticleListRenderer)
    def list(self) -> list[OperationResult]:
        ...

    @with_renderer_class(ArticleCreateRenderer)
    def create(self, title: str) -> list[OperationResult]:
        ...
```

**Priorité de résolution du renderer :**
1. `@with_renderer_class` sur la méthode
2. Dict `renderers` de la classe
3. `renderer_class` (fallback)

**Pourquoi pas `renderer_class` ?** Collision possible avec l'attribut de fallback
`self.renderer_class` — voir Design > Note de conception ci-dessus pour le détail du
mécanisme.
```

- [ ] **Étape 2 : Mettre à jour les exemples dans `docs/examples.md`**

Repérer un exemple qui utilise `self.respond("method_name", ...)` et le mettre à jour
pour utiliser `self.respond(self.method_name, ...)`. Ajouter une note de migration pour
les utilisateurs existants.

---

## Tâche 6 : Lint et commit

- [ ] **Étape 1 : Ruff**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

- [ ] **Étape 2 : Commit**

```bash
git add src/ tests/core/interfaces/ docs/api/interfaces.md docs/examples.md
git commit -m "$(cat <<'EOF'
✨ feat(interfaces): typed callable dispatch in BaseInterface.respond()

- respond() now accepts a bound method alongside the legacy method name string
- @with_renderer_class(MyRenderer) attaches renderer directly on the method
- Named distinctly from the renderer_class fallback attribute to avoid
  class-body name shadowing when both are declared on the same subclass
- Renderer resolution: @with_renderer_class > renderers dict > renderer_class
- Fully backward compatible — existing string calls unchanged
EOF
)"
```

---

## Tâche 7 : Migrer le scaffolding vers le pattern typé

Le scaffolding (`pyclifer project add command`) génère aujourd'hui l'ancien pattern
(`respond("name")` + dict `renderers`). Pour que le framework dogfood son propre pattern
recommandé, les nouveaux projets générés doivent utiliser `@with_renderer_class` et le
dispatch callable. Les projets déjà scaffoldés avec l'ancien sentinel `# --- renderers ---`
doivent continuer à fonctionner sans migration manuelle — `_wire_interface_method` détecte
lequel des deux sentinels est présent et injecte en conséquence.

**Fichiers à modifier :**

| Fichier | Changement |
|---------|-----------|
| `src/pyclifer/apps/project/templates/app_interfaces.py.jinja2` | Retirer le dict `renderers` + son sentinel, importer `with_renderer_class` |
| `src/pyclifer/apps/project/templates/app_interfaces_with_core.py.jinja2` | Idem |
| `src/pyclifer/apps/project/templates/command.py.jinja2` | `iface = X(ctx); return iface.respond(iface.name)` au lieu de `respond("name")` |
| `src/pyclifer/apps/project/interfaces.py` | `_wire_interface_method` détecte ancien/nouveau sentinel et injecte en conséquence |
| `tests/apps/project/test_interfaces.py` | Nouveaux tests pour les deux branches |
| `docs/scaffolding.md` | Exemples générés mis à jour |

- [ ] **Étape 1 : Écrire les tests échouants dans `tests/apps/project/test_interfaces.py`**

```python
class TestWireInterfaceMethod:
    """_wire_interface_method injects a renderer for the new command — both template styles."""

    def test_new_template_injects_with_renderer_class_decorator(self, project, tmp_path) -> None:
        """Current template (no renderers dict) gets the decorator directly on the method."""
        list(project.add_app("repos"))
        list(project.add_command("list", "repos"))
        path = tmp_path / "my-app" / "src" / "my_app" / "apps" / "repos" / "interfaces.py"
        content = path.read_text()
        assert "@with_renderer_class(RepoRenderer)" in content
        assert "def list(self)" in content
        assert "renderers = {" not in content

    def test_legacy_template_still_injects_into_renderers_dict(self, project, tmp_path) -> None:
        """Pre-existing projects with the old renderers dict sentinel keep working."""
        list(project.add_app("repos"))
        interfaces_path = (
            tmp_path / "my-app" / "src" / "my_app" / "apps" / "repos" / "interfaces.py"
        )
        legacy_content = interfaces_path.read_text().replace(
            "    # --- commands --- (used by `pyclifer project add command` — do not remove)",
            "    renderers = {\n"
            "        # --- renderers --- (used by `pyclifer project add command` — do not remove)\n"
            "    }\n\n"
            "    # --- commands --- (used by `pyclifer project add command` — do not remove)",
        )
        interfaces_path.write_text(legacy_content)

        list(project.add_command("list", "repos"))
        content = interfaces_path.read_text()
        assert '"list": RepoRenderer,' in content
        assert "@with_renderer_class" not in content


class TestCommandTemplateTypedDispatch:
    """Generated command.py files call respond() with the bound method."""

    def test_generated_command_uses_typed_dispatch(self, project, tmp_path) -> None:
        list(project.add_app("repos"))
        list(project.add_command("list", "repos"))
        path = tmp_path / "my-app" / "src" / "my_app" / "apps" / "repos" / "commands" / "list.py"
        content = path.read_text()
        assert "iface = RepoInterface(ctx)" in content
        assert "return iface.respond(iface.list)" in content
        assert 'respond("list")' not in content
```

Note : ajuster les noms exacts (`RepoRenderer`, `RepoInterface`) si `_names()` produit une
autre forme pour `"repos"` — vérifier en exécutant le test une première fois.

- [ ] **Étape 2 : Confirmer l'échec**

```bash
python -m pytest tests/apps/project/test_interfaces.py -v
```

- [ ] **Étape 3 : Modifier les templates**

`templates/app_interfaces.py.jinja2` et `templates/app_interfaces_with_core.py.jinja2` —
retirer le dict `renderers` et son sentinel, ajouter `with_renderer_class` à l'import :

```python
from pyclifer import BaseInterface, BaseRenderer, OperationResult, with_renderer_class

# ...

class {{ name_singular_pascal }}Interface(BaseInterface):
    """Interface for {{ name_pascal }} business logic."""

    # --- commands --- (used by `pyclifer project add command` — do not remove)
```

`templates/command.py.jinja2` :

```python
from pyclifer import Response, command

from ....core.context import pass_cli_context
from ..interfaces import {{ app_pascal }}Interface


@command()
@pass_cli_context
def {{ name_snake }}(ctx) -> Response:
    """{{ name_pascal }} description."""
    iface = {{ app_pascal }}Interface(ctx)
    return iface.respond(iface.{{ name_snake }})
```

- [ ] **Étape 4 : Modifier `_wire_interface_method` dans `src/pyclifer/apps/project/interfaces.py`**

Détecter `"# --- renderers ---" in content` pour choisir la branche legacy (dict, comportement
inchangé) ou la branche actuelle (décorateur `@with_renderer_class` injecté directement
au-dessus de la méthode, import `with_renderer_class` ajouté si absent). Le sentinel
`# --- commands ---` reste le seul point d'ancrage commun aux deux branches.

- [ ] **Étape 5 : Tous les tests passent**

```bash
python -m pytest tests/ -v
```

- [ ] **Étape 6 : Mettre à jour `docs/scaffolding.md`**

Remplacer l'exemple de fichier généré (`interfaces.py` et `command.py`) par les nouvelles
versions ci-dessus.

- [ ] **Étape 7 : Lint et commit séparé**

```bash
ruff check src/ tests/
ruff format src/ tests/
git add src/pyclifer/apps/project/ tests/apps/project/ docs/scaffolding.md
git commit -m "$(cat <<'EOF'
✨ feat(scaffolding): generate typed dispatch in new projects

- command.py.jinja2 now calls respond(iface.method) instead of respond("method")
- app_interfaces.py.jinja2 drops the renderers dict in favor of @with_renderer_class
- _wire_interface_method supports both sentinels — projects scaffolded before this
  change keep working against the legacy renderers dict, unmodified
EOF
)"
```