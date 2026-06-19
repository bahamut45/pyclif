# Support async def transparent dans les commandes pyclifer

**Objectif :** Permettre l'utilisation de `async def` dans les commandes pyclifer sans aucun
changement pour l'utilisateur. `returns_response` détecte les coroutines et les exécute via
`asyncio.run()` automatiquement.

**Cas d'usage cible :**

```python
@app.command()
@returns_response
@pass_cli_context
async def fetch(ctx, url: str):
    data = await httpx.AsyncClient().get(url).json()
    return Response(success=True, message="ok", data=data)
```

**Stack :** asyncio (stdlib), inspect (stdlib), pytest-asyncio (tests uniquement)

---

## Design

### Décision : asyncio uniquement

`asyncio` est stdlib, couvre 99 % des cas CLI réels. `anyio` / `trio` hors scope.

### Décision : correction dans `returns_response`

`returns_response` est le point de passage central de tous les résultats de commande.
C'est l'endroit minimal et correct pour intercepter une coroutine retournée par une
`async def`.

Click appelle la fonction synchrone ; si la fonction est `async def`, `f(*args, **kwargs)`
retourne un objet coroutine au lieu du résultat. La détection doit se faire
**après l'appel** via `inspect.iscoroutine(result)`.

```python
# Dans returns_response.wrapper() :
result = f(*args, **kwargs)
if inspect.iscoroutine(result):
    import asyncio
    result = asyncio.run(result)
```

### Portée

- Commandes avec `@returns_response` : couvert.
- Commandes `command(handle_response=True)` : couvert (délègue à `returns_response`).
- Commandes async sans `returns_response` (pas de valeur de retour) : hors scope — Click
  ne sait pas quoi faire d'une coroutine, mais c'est un usage sans `returns_response` donc
  déjà hors convention pyclifer.

### Gestion d'erreur

Si une boucle événementielle est déjà active (`asyncio.run()` lèverait `RuntimeError`),
l'exception remonte normalement dans le bloc `try/except` de `returns_response` et est
transformée en `Response(success=False, ...)`. Ce cas ne se produit pas en CLI standard.

---

## Fichiers à modifier

| Fichier | Changement |
|---------|-----------|
| `src/pyclifer/core/decorators.py` | Ajouter `import inspect` + détection coroutine dans `wrapper()` |
| `tests/core/test_decorators.py` | Nouveaux tests async |

---

## Tâche 1 : Créer la branche et écrire les tests échouants

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/async-command-support
```

- [ ] **Étape 2 : Écrire les tests (doivent échouer)**

Dans `tests/core/test_decorators.py`, ajouter une classe `TestAsyncCommand` :

```python
import asyncio
from unittest.mock import MagicMock, patch

class TestAsyncCommand:
    """Tests for async def command support in returns_response."""

    def test_async_command_returns_response(self, cli_runner_ctx):
        """returns_response transparently runs an async command and prints the Response."""
        from pyclifer import Response, returns_response

        @returns_response
        async def my_cmd(ctx):
            return Response(success=True, message="async ok", data={})

        with patch("pyclifer.core.decorators.BaseContext") as mock_ctx_cls:
            mock_ctx = MagicMock()
            mock_ctx_cls.return_value = mock_ctx
            with patch("click_extra.get_current_context", return_value=None):
                my_cmd(None)

        mock_ctx.print_result_based_on_format.assert_called_once()
        response_arg = mock_ctx.print_result_based_on_format.call_args[0][0]
        assert response_arg.success is True
        assert response_arg.message == "async ok"

    def test_async_command_exception_is_caught(self):
        """Unhandled exception in async command becomes a failure Response."""
        from pyclifer import returns_response

        @returns_response
        async def bad_cmd():
            raise ValueError("boom")

        with patch("pyclifer.core.decorators.BaseContext") as mock_ctx_cls:
            mock_ctx = MagicMock()
            mock_ctx_cls.return_value = mock_ctx
            with patch("click_extra.get_current_context", return_value=None):
                bad_cmd()

        response_arg = mock_ctx.print_result_based_on_format.call_args[0][0]
        assert response_arg.success is False
        assert "boom" in response_arg.message

    def test_sync_command_unaffected(self):
        """Existing sync commands continue to work without change."""
        from pyclifer import Response, returns_response

        @returns_response
        def sync_cmd():
            return Response(success=True, message="sync ok", data={})

        with patch("pyclifer.core.decorators.BaseContext") as mock_ctx_cls:
            mock_ctx = MagicMock()
            mock_ctx_cls.return_value = mock_ctx
            with patch("click_extra.get_current_context", return_value=None):
                sync_cmd()

        response_arg = mock_ctx.print_result_based_on_format.call_args[0][0]
        assert response_arg.success is True
        assert response_arg.message == "sync ok"
```

- [ ] **Étape 3 : Confirmer l'échec**

```bash
python -m pytest tests/core/test_decorators.py::TestAsyncCommand -v
```

Attendu : `FAILED` — la coroutine n'est pas exécutée, `result` n'est pas une `Response`.

---

## Tâche 2 : Implémenter le support async dans `returns_response`

**Fichier :** `src/pyclifer/core/decorators.py`

- [ ] **Étape 1 : Ajouter `import inspect` en tête du fichier**

Après `import functools` et `import logging`, ajouter :

```python
import inspect
```

- [ ] **Étape 2 : Ajouter la détection coroutine dans `wrapper()`**

Dans la fonction `wrapper()` de `returns_response`, localiser :

```python
        try:
            result = f(*args, **kwargs)
        except Exception as e:
```

Remplacer par :

```python
        try:
            result = f(*args, **kwargs)
            if inspect.iscoroutine(result):
                import asyncio  # noqa: PLC0415 — lazy import, asyncio only needed for async commands
                result = asyncio.run(result)
        except Exception as e:
```

- [ ] **Étape 3 : Lancer les tests**

```bash
python -m pytest tests/core/test_decorators.py::TestAsyncCommand -v
```

Attendu : tous les tests `TestAsyncCommand` passent.

---

## Tâche 3 : Tests de couverture complète

- [ ] **Étape 1 : S'assurer que tous les tests existants passent**

```bash
python -m pytest tests/ -v
```

- [ ] **Étape 2 : Vérifier la couverture de la branche ajoutée**

```bash
python -m pytest tests/core/test_decorators.py -v --cov=src/pyclifer/core/decorators --cov-report=term-missing
```

La ligne `if inspect.iscoroutine(result):` doit être couverte par les deux branches
(True pour les tests async, False pour les tests sync existants).

---

## Tâche 4 : Documentation

**Fichier :** `docs/getting-started.md`

- [ ] **Étape 1 : Ajouter une section "Commandes asynchrones"**

Repérer la section qui décrit l'écriture d'une commande (là où `@returns_response` est
présenté). Ajouter après :

```markdown
### Commandes asynchrones

pyclifer supporte nativement les `async def` — aucune configuration requise.
`returns_response` détecte automatiquement une coroutine et l'exécute via `asyncio.run()`.

```python
@app.command()
@returns_response
@pass_cli_context
async def fetch(ctx):
    async with httpx.AsyncClient() as client:
        data = (await client.get("https://api.example.com/items")).json()
    return Response(success=True, message="Fetched", data=data)
```

> **Note :** asyncio uniquement. Si une boucle événementielle est déjà active dans
> votre contexte d'exécution, appelez `asyncio.get_event_loop().run_until_complete()`
> manuellement à la place.
```

---

## Tâche 5 : Lint et commit

- [ ] **Étape 1 : Ruff**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

- [ ] **Étape 2 : Stager et committer**

```bash
git add src/pyclifer/core/decorators.py tests/core/test_decorators.py docs/getting-started.md
git commit -m "$(cat <<'EOF'
✨ feat(decorators): support async def commands in returns_response

- Detect coroutine return value via inspect.iscoroutine() after f() call
- Execute with asyncio.run() transparently — no user-facing change required
- Unhandled async exceptions flow through the existing try/except path
EOF
)"
```