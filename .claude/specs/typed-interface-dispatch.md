# Dispatch typé sur `BaseInterface.respond()`

**Objectif :** Éliminer la string `"method_name"` dans `interface.respond("list", ...)`.
Accepter directement un callable : `interface.respond(interface.list, ...)`. Ajouter un
décorateur `@interface_method(renderer=MyRenderer)` pour attacher le renderer directement
sur la méthode — plus besoin du dict `renderers` de classe.

**Avant / Après :**

```python
# Avant — fragile, pas de complétion IDE
return self.respond("list", page=page, limit=limit)

# Après — typé, refactorable, complétion IDE
return self.respond(self.list, page=page, limit=limit)

# Avec décorateur — renderer colocalisé avec la méthode
class ArticleInterface(BaseInterface):
    @interface_method(renderer=ArticleListRenderer)
    def list(self) -> list[OperationResult]: ...
```

**Stack :** stdlib uniquement. Rétrocompatible avec la signature string existante.

---

## Design

### Priorité de résolution du renderer

1. Attribut `_pyclifer_renderer` sur la méthode (posé par `@interface_method`)
2. Dict `self.renderers` (comportement actuel)
3. `self.renderer_class` (fallback actuel)

### `respond()` avec callable

Quand un callable est passé :
- Extraire `__name__` pour la résolution du renderer via `renderers`
- Détecter `_pyclifer_renderer` sur le callable avant le dict
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

### `@interface_method` décorateur

Fonction simple qui pose un attribut sur la méthode :

```python
def interface_method(
    renderer: type[BaseRenderer],
) -> Callable[[_F], _F]:
    def decorator(f: _F) -> _F:
        f._pyclifer_renderer = renderer
        return f
    return decorator
```

---

## Fichiers à modifier

| Fichier | Changement |
|---------|-----------|
| `src/pyclifer/core/interfaces/base.py` | Modifier `respond()`, ajouter `interface_method` |
| `src/pyclifer/__init__.py` | Exporter `interface_method` dans `__all__` |
| `tests/core/interfaces/test_base.py` | Nouveaux tests (nouveau fichier ou extension) |

---

## Tâche 1 : Créer la branche et écrire les tests échouants

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/typed-interface-dispatch
```

- [ ] **Étape 2 : Créer `tests/core/interfaces/test_base.py`**

```python
"""Tests for BaseInterface.respond() with callable dispatch and @interface_method."""
import pytest
from unittest.mock import MagicMock
from pyclifer.core.interfaces.base import BaseInterface, interface_method
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

    @interface_method(renderer=AltRenderer)
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

    def test_respond_with_callable_uses_interface_method_renderer(self):
        iface = MyInterface(ctx=MagicMock())
        response = iface.respond(iface.search, "query")
        assert isinstance(response.renderer, AltRenderer)

    def test_respond_with_callable_returns_correct_data(self):
        iface = MyInterface(ctx=MagicMock())
        response = iface.respond(iface.fetch, 99)
        assert response.data["results"][0].data == {"name": "Alice"}


class TestInterfaceMethodDecorator:
    """@interface_method attaches a renderer to a method."""

    def test_decorator_sets_pyclifer_renderer_attribute(self):
        iface = MyInterface(ctx=MagicMock())
        assert hasattr(iface.search, "_pyclifer_renderer")
        assert iface.search._pyclifer_renderer is AltRenderer

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

Attendu : `ImportError: cannot import name 'interface_method' from 'pyclifer.core.interfaces.base'`

---

## Tâche 2 : Modifier `BaseInterface` et ajouter `interface_method`

**Fichier :** `src/pyclifer/core/interfaces/base.py`

- [ ] **Étape 1 : Ajouter les imports manquants en tête du fichier**

```python
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar, TypeVar

_F = TypeVar("_F", bound=Callable)
```

- [ ] **Étape 2 : Ajouter la fonction `interface_method` avant la classe `BaseInterface`**

```python
def interface_method(renderer: type[BaseRenderer]) -> Callable[[_F], _F]:
    """Attach a renderer class to an interface method.

    The renderer takes priority over the class-level renderers dict in respond().
    This co-locates the renderer declaration with the method it belongs to,
    making the renderers dict optional.

    Args:
        renderer: The BaseRenderer subclass to use for this method's output.

    Returns:
        A decorator that attaches _pyclifer_renderer to the function.
    """

    def decorator(f: _F) -> _F:
        """Attach the renderer to the function."""
        f._pyclifer_renderer = renderer  # type: ignore[attr-defined]
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
        1. _pyclifer_renderer attribute on the callable (set by @interface_method)
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
            # Priority 1: renderer attached via @interface_method
            renderer_cls = getattr(method, "_pyclifer_renderer", None)
            if renderer_cls is None:
                # Priority 2: renderers dict, then renderer_class fallback
                renderer_cls = self.renderers.get(method_name, self.renderer_class)
        else:
            method_name = method_or_name
            method = getattr(self, method_name)
            renderer_cls = getattr(method, "_pyclifer_renderer", None)
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

## Tâche 3 : Exporter `interface_method` depuis `pyclifer.__init__`

**Fichier :** `src/pyclifer/__init__.py`

- [ ] **Étape 1 : Ajouter l'import**

```python
from .core.interfaces import BaseInterface, interface_method
```

- [ ] **Étape 2 : Ajouter dans `__all__`**

```python
    "interface_method",
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

## Tâche 5 : Lint et commit

- [ ] **Étape 1 : Ruff**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

- [ ] **Étape 2 : Commit**

```bash
git add src/ tests/core/interfaces/
git commit -m "$(cat <<'EOF'
✨ feat(interfaces): typed callable dispatch in BaseInterface.respond()

- respond() now accepts a bound method alongside the legacy method name string
- @interface_method(renderer=MyRenderer) attaches renderer directly on the method
- Renderer resolution: @interface_method > renderers dict > renderer_class
- Fully backward compatible — existing string calls unchanged
EOF
)"
```