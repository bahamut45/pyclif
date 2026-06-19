# Format de sortie CSV

**Objectif :** Ajouter `csv` comme format de sortie valide dans `--output-format`.
Permet aux utilisateurs de piper la sortie vers Excel, Google Sheets, ou des outils
de traitement de données.

**Cas d'usage cible :**

```bash
myapp articles list -o csv > articles.csv
myapp users list -o csv | xsv table
```

**Stack :** stdlib `csv`, `io` uniquement — aucune dépendance supplémentaire.

---

## Design

### Décision : `csv` via `BaseRenderer.csv()`

Même pattern que `table()`, `raw()`, `text()` : une méthode sur `BaseRenderer` que
`OutputFormatMixin` dispatche. L'implémentation par défaut serialise `response.data["results"]`
ligne par ligne avec les colonnes de `get_columns()`.

### Sortie

- En-tête : noms des colonnes (de `get_columns()`, fallback `get_fields()`).
- Corps : une ligne par `OperationResult`, valeurs extraites via `_result_to_row()`.
- Valeurs `None` → chaîne vide.
- Séparateur : virgule (RFC 4180). Pas de support du séparateur configurable (hors scope).
- Affiché via `console.print()` sans highlight (texte brut).

### Integration dans le dispatch

```python
"csv": lambda: self._print_csv(renderer.csv(result)),
```

### Filtre `--output-filter` avec CSV

Non supporté pour `csv` (hors scope). Le filtre dotted-path est conçu pour JSON/YAML/raw.
Si `--output-filter` est passé avec `-o csv`, il est ignoré silencieusement (cohérent avec
le comportement actuel pour `text` et `rich`).

---

## Fichiers à modifier

| Fichier | Changement |
|---------|-----------|
| `src/pyclifer/core/decorators.py` | Ajouter `"csv"` à la liste `Choice` |
| `src/pyclifer/core/output/renderer.py` | Ajouter `csv()` sur `BaseRenderer` et `ResponseRenderer` |
| `src/pyclifer/core/mixins/output.py` | Ajouter `_print_csv()` et le dispatch `"csv"` |
| `tests/core/mixins/test_output.py` | Nouveaux tests CSV |

---

## Tâche 1 : Créer la branche et écrire les tests échouants

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/csv-output-format
```

- [ ] **Étape 2 : Écrire les tests**

Dans `tests/core/mixins/test_output.py`, ajouter une classe `TestCsvOutputFormat` :

```python
import csv
import io
from unittest.mock import MagicMock
from pyclifer import Response, CliTable, CliTableColumn
from pyclifer.core.output.renderer import BaseRenderer
from pyclifer.core.output.responses import OperationResult
from pyclifer.core.mixins.output import OutputFormatMixin


def make_response_with_results(items: list[dict]) -> Response:
    results = [OperationResult(success=True, item=str(i), data=d) for i, d in enumerate(items)]
    return Response(success=True, message="ok", data={"results": results})


class MyRenderer(BaseRenderer):
    fields = ["name", "age"]
    columns = ["name", "age"]


class TestCsvOutputFormat:
    """--output-format csv renders results as RFC 4180 CSV."""

    def test_csv_has_header_row(self):
        response = make_response_with_results([{"name": "Alice", "age": 30}])
        response.renderer = MyRenderer()

        ctx = OutputFormatMixin()
        ctx.output_format = "csv"
        ctx.console = MagicMock()

        ctx.print_result_based_on_format(response)

        printed = ctx.console.print.call_args[0][0]
        lines = printed.strip().splitlines()
        assert lines[0] == "name,age"

    def test_csv_has_data_rows(self):
        response = make_response_with_results([
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ])
        response.renderer = MyRenderer()

        ctx = OutputFormatMixin()
        ctx.output_format = "csv"
        ctx.console = MagicMock()

        ctx.print_result_based_on_format(response)

        printed = ctx.console.print.call_args[0][0]
        lines = printed.strip().splitlines()
        assert lines[1] == "Alice,30"
        assert lines[2] == "Bob,25"

    def test_csv_none_values_become_empty_string(self):
        response = make_response_with_results([{"name": "Alice", "age": None}])
        response.renderer = MyRenderer()

        ctx = OutputFormatMixin()
        ctx.output_format = "csv"
        ctx.console = MagicMock()

        ctx.print_result_based_on_format(response)

        printed = ctx.console.print.call_args[0][0]
        lines = printed.strip().splitlines()
        assert lines[1] == "Alice,"

    def test_csv_values_with_commas_are_quoted(self):
        response = make_response_with_results([{"name": "Smith, John", "age": 40}])
        response.renderer = MyRenderer()

        ctx = OutputFormatMixin()
        ctx.output_format = "csv"
        ctx.console = MagicMock()

        ctx.print_result_based_on_format(response)

        printed = ctx.console.print.call_args[0][0]
        reader = csv.DictReader(io.StringIO(printed))
        rows = list(reader)
        assert rows[0]["name"] == "Smith, John"

    def test_base_renderer_csv_returns_string(self):
        renderer = MyRenderer()
        response = make_response_with_results([{"name": "Alice", "age": 30}])
        response.renderer = renderer

        result = renderer.csv(response)
        assert isinstance(result, str)
        assert "name,age" in result
        assert "Alice" in result
```

- [ ] **Étape 3 : Confirmer l'échec**

```bash
python -m pytest tests/core/mixins/test_output.py::TestCsvOutputFormat -v
```

Attendu : `AttributeError: 'BaseRenderer' object has no attribute 'csv'`

---

## Tâche 2 : Ajouter `csv()` sur `BaseRenderer` et `ResponseRenderer`

**Fichier :** `src/pyclifer/core/output/renderer.py`

- [ ] **Étape 1 : Ajouter `import csv` et `import io` en tête du fichier**

- [ ] **Étape 2 : Ajouter la méthode `csv()` dans `ResponseRenderer` (Protocol)**

Après `def raw(...)`:

```python
    def csv(self, response: Response) -> str:
        """Return the response results as a CSV string (header + rows)."""
        ...
```

- [ ] **Étape 3 : Ajouter la méthode `csv()` dans `BaseRenderer`**

Après la méthode `raw()` :

```python
    def csv(self, response: Response) -> str:
        """Return response results as a RFC 4180 CSV string.

        Header row uses get_columns(). Each OperationResult is serialized via
        _result_to_row(). None values are written as empty strings.

        Args:
            response: The command response carrying the result list.

        Returns:
            CSV-formatted string with header and data rows.
        """
        cols = self.get_columns()
        results = response.data.get("results", [])
        rows = [self._result_to_row(r, cols) for r in results]

        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=cols,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
        return buf.getvalue()
```

---

## Tâche 3 : Ajouter `_print_csv()` et le dispatch dans `OutputFormatMixin`

**Fichier :** `src/pyclifer/core/mixins/output.py`

- [ ] **Étape 1 : Ajouter `_print_csv()` à `OutputFormatMixin`**

Après `_print_yaml()` :

```python
    def _print_csv(self, data: str) -> None:
        """Print a CSV string to the console without syntax highlighting.

        Args:
            data: CSV-formatted string to print.
        """
        self.console.print(data, soft_wrap=True, highlight=False, markup=False)  # type: ignore[attr-defined]
```

- [ ] **Étape 2 : Ajouter `"csv"` dans le dict `dispatch`**

Dans `print_result_based_on_format()`, localiser le dict `dispatch` et ajouter :

```python
            "csv": lambda: self._print_csv(renderer.csv(result)),
```

---

## Tâche 4 : Ajouter `"csv"` au `Choice` dans `output_format_option()`

**Fichier :** `src/pyclifer/core/decorators.py`

- [ ] **Étape 1 : Mettre à jour la liste `Choice`**

Localiser :

```python
        click_extra.Choice(["json", "yaml", "table", "rich", "raw", "text"], case_sensitive=False),
```

Remplacer par :

```python
        click_extra.Choice(["json", "yaml", "table", "rich", "raw", "text", "csv"], case_sensitive=False),
```

---

## Tâche 5 : Vérification complète

- [ ] **Étape 1 : Tous les tests passent**

```bash
python -m pytest tests/ -v
```

- [ ] **Étape 2 : Test manuel**

```bash
python -c "
from click.testing import CliRunner
from pyclifer import app_group, command, returns_response, Response, pass_context
from pyclifer.core.output.renderer import BaseRenderer
from pyclifer.core.output.responses import OperationResult

class MyRenderer(BaseRenderer):
    columns = ['name', 'score']

@app_group(add_version_option=False)
@pass_context
def cli(ctx): pass

@cli.command()
@returns_response
@pass_context
def list_items(ctx):
    results = [
        OperationResult(success=True, item='1', data={'name': 'Alice', 'score': 95}),
        OperationResult(success=True, item='2', data={'name': 'Bob', 'score': 87}),
    ]
    return Response.from_results(results, renderer=MyRenderer())

runner = CliRunner()
result = runner.invoke(cli, ['list-items', '-o', 'csv'])
print(result.output)
"
```

Sortie attendue :
```
name,score
Alice,95
Bob,87
```

---

## Tâche 6 : Documentation

**Fichiers :** `docs/output-formatting.md`, `docs/api/output.md`

- [ ] **Étape 1 : Ajouter `csv` dans le tableau des formats — `docs/output-formatting.md`**

Repérer le tableau ou la liste qui présente les formats disponibles
(`json`, `yaml`, `table`, `rich`, `raw`, `text`). Ajouter la ligne csv :

```markdown
| `csv` | RFC 4180 CSV avec en-tête — idéal pour Excel / Google Sheets / `xsv` |
```

Ajouter aussi un exemple d'usage :

```markdown
### CSV

```bash
myapp articles list -o csv > articles.csv
myapp articles list -o csv | xsv table
```

L'en-tête utilise les colonnes déclarées dans `BaseRenderer.columns`.
Les valeurs `None` sont écrites comme chaînes vides.
Les valeurs contenant des virgules sont automatiquement quotées (RFC 4180).
```

- [ ] **Étape 2 : Documenter `BaseRenderer.csv()` dans `docs/api/output.md`**

Dans la section `BaseRenderer`, ajouter `csv()` parmi les méthodes de rendu.

---

## Tâche 7 : Lint et commit

- [ ] **Étape 1 : Ruff**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

- [ ] **Étape 2 : Commit**

```bash
git add src/ tests/ docs/output-formatting.md docs/api/output.md
git commit -m "$(cat <<'EOF'
✨ feat(output): add csv output format

- BaseRenderer.csv() serializes results to RFC 4180 CSV string
- OutputFormatMixin._print_csv() prints without syntax highlighting
- output_format_option Choice list extended with 'csv'
- None values serialize as empty strings; values with commas auto-quoted
EOF
)"
```