# Doc Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all findings from the `/doc-review` audit — 1 critical, 3 moderate, 8 minor issues across 4 doc files.

**Architecture:** Documentation-only changes. No code touched. Each task is one file, one commit. Verify with `mkdocs build --strict` after each task.

**Tech Stack:** MkDocs + mkdocstrings, Markdown.

---

## Files Modified

| File | Tasks | Issues fixed |
|------|-------|-------------|
| `docs/getting-started.md` | 1, 2 | CRITICAL Step 3 group wiring + MODERATE Response pattern |
| `docs/api/decorators.md` | 3 | MODERATE `option(store_in_meta)` + MINOR `command(handle_response)`, `app_group` params |
| `docs/logging.md` | 4 | MODERATE `DEFAULT_FIELDS` full list + MINOR `PYCLIFER_LOG_LEVELS` value |
| `docs/output-formatting.md` | 5 | MINOR `BaseRenderer.model_class`, `datetime_format`, `date_format` |

---

## Task 1: Fix broken group example in getting-started.md [CRITICAL]

**Files:**
- Modify: `docs/getting-started.md:118-137` (Step 3)

Step 3 defines `@group(name="database")` standalone — never attached to the parent `cli` group. Step 4 calls `cli()` but `database` is unreachable. Fix: rewrite Step 3 to use `@cli.group() / @group(...)` double-decorator pattern (same as `examples.md:51-52`) and make Step 4 show a complete runnable block.

- [ ] **Step 1: Replace Step 3 example**

In `docs/getting-started.md`, replace lines 118–137:

```markdown
### Step 3: Add a command group

```python
from pyclifer import app_group, group, option


@app_group(name="myapp", auto_envvar_prefix="MYAPP")
def cli():
    """My Application."""
    pass


@cli.group()
@group(name="database")
def database():
    """Database management commands."""
    pass


@database.command()
@option("--url", "-u", required=True, help="Database URL")
@option("--timeout", "-t", type=int, default=30, help="Connection timeout")
def connect(url, timeout):
    """Connect to the database."""
    print(f"Connecting to {url} with timeout {timeout}s")
```
```

- [ ] **Step 2: Fix Step 4 to show the full entrypoint**

Replace the current Step 4:

```markdown
### Step 4: Run your CLI

```python
if __name__ == "__main__":
    cli()
```
```

- [ ] **Step 3: Verify build**

```bash
mkdocs build --strict 2>&1 | grep -E "WARNING|ERROR"
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add docs/getting-started.md
git commit -m "📝 docs(getting-started): fix standalone @group example missing parent wiring"
```

---

## Task 2: Add Response pattern to getting-started.md [MODERATE]

**Files:**
- Modify: `docs/getting-started.md` (after the minimal `print()` example, ~line 68)

The minimal example uses `print()`, which works but teaches the wrong pattern. Add a "Using Response" subsection right after, showing the canonical `return Response(...)` approach with `handle_response=True` (the default).

- [ ] **Step 1: Add Response subsection after the minimal example**

After the `Save this as my_cli.py and run it:` block (around line 79), insert:

```markdown
### Using Response (recommended pattern)

pyclifer commands ideally return a `Response` object instead of printing directly.
`@app_group` enables `handle_response=True` by default, so the framework prints the response
automatically in the right format (`--output-format json`, `--output-format table`, etc.):

```python
from pyclifer import app_group, option, Response


@app_group()
def main():
    """My CLI application."""
    pass


@main.command()
@option("--name", "-n", help="Your name")
def hello(name):
    """Say hello."""
    return Response(success=True, message=f"Hello {name or 'World'}!")


if __name__ == "__main__":
    main()
```

Try it with different formats:

```bash
python my_cli.py hello --name "Alice"
python my_cli.py hello --name "Alice" -o json
python my_cli.py hello --name "Alice" -o table
```

See [Output Formatting](output-formatting.md) for the full output system.
```

- [ ] **Step 2: Verify build**

```bash
mkdocs build --strict 2>&1 | grep -E "WARNING|ERROR"
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add docs/getting-started.md
git commit -m "📝 docs(getting-started): add Response pattern example alongside print() minimal"
```

---

## Task 3: Document missing parameters in api/decorators.md [MODERATE + MINOR]

**Files:**
- Modify: `docs/api/decorators.md`

Three gaps:
1. `option(store_in_meta=...)` — not in the `option()` bullet list
2. `command(handle_response=True)` — parameter exists in code, absent from docs
3. `app_group(auto_envvar_prefix, rich_help_config, use_rich_help)` — three undocumented `GroupConfig` pass-throughs

- [ ] **Step 1: Add `store_in_meta` to option() section**

In `docs/api/decorators.md`, in the `## option` section, add to the bullet list (after `show_in_subcommand_help`):

```markdown
- `store_in_meta=False` — when `True`, stores the option value in `ctx.meta` automatically
  (key: `"pyclifer.<option-name>"`). The option is not exposed as a function parameter.
  Used internally by `pagination_options` for `--page` and `--limit`.
```

- [ ] **Step 2: Add `handle_response` to command() section**

In `docs/api/decorators.md`, in the `## command` section, add before the `:::` directive:

```markdown
Key parameter:

- `handle_response=False` — when `True`, wraps the command with `returns_response` so any
  `Response` returned by the function is printed automatically. Equivalent to stacking
  `@returns_response` manually.
```

- [ ] **Step 3: Add undocumented app_group params**

In `docs/api/decorators.md`, in the `## app_group` section, add to the `Key parameters` list:

```markdown
- `auto_envvar_prefix` — uppercase prefix for automatic environment variable binding.
  With `auto_envvar_prefix="MYAPP"`, `--database-url` reads `MYAPP_DATABASE_URL`.
- `rich_help_config` — `RichHelpConfiguration` instance (or dict) forwarded to rich-click.
  Lets you customise colours, column widths, and panel styles in `--help` output.
- `use_rich_help` — set to `False` to disable rich-click rendering and use plain Click help.
  Defaults to `True`.
```

- [ ] **Step 4: Verify build**

```bash
mkdocs build --strict 2>&1 | grep -E "WARNING|ERROR"
```

Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add docs/api/decorators.md
git commit -m "📝 docs(api/decorators): document store_in_meta, handle_response, and app_group kwargs"
```

---

## Task 4: Complete logging.md — DEFAULT_FIELDS list and log utilities [MODERATE + MINOR]

**Files:**
- Modify: `docs/logging.md`

Two gaps:
1. `SecretsMasker.DEFAULT_FIELDS` — partial list with "etc." Replace with the full set.
2. `PYCLIFER_LOG_LEVELS`, `add_trace_method`, `RichExtraFormatter`, `RichExtraStreamHandler` — listed in the intro bullet list but never shown in examples.

- [ ] **Step 1: Replace partial DEFAULT_FIELDS list with full list**

In `docs/logging.md`, replace lines ~148-149:

Current:
```markdown
`SecretsMasker` ships with a built-in set of field names it always masks (`password`, `api_key`,
`token`, `secret`, `access_token`, etc.). Pass `sensitive_fields` to extend this list — the
defaults are never removed.
```

Replace with:

```markdown
`SecretsMasker` ships with a built-in set of field names it always masks. Pass `sensitive_fields`
to extend this list — the defaults are never removed.

Default masked fields (`SecretsMasker.DEFAULT_FIELDS`):

```
access_token, api_key, apikey, authorization, keyfile_dict,
passphrase, passwd, password, private_key, pwd,
secret, service_account, token
```
```

- [ ] **Step 2: Add PYCLIFER_LOG_LEVELS value**

In `docs/logging.md`, find the bullet that mentions `PYCLIFER_LOG_LEVELS` (around line 23) and add a note or a new subsection (after the existing logging levels table, if any) showing the value:

```markdown
`PYCLIFER_LOG_LEVELS` extends click-extra's standard levels with `TRACE`:

```python
from pyclifer import PYCLIFER_LOG_LEVELS
# {"TRACE": 5, "DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
```
```

- [ ] **Step 3: Add brief usage note for add_trace_method / RichExtraFormatter / RichExtraStreamHandler**

Find the section where these are mentioned (around line 24-32) and add a short example after the bullet list:

```markdown
For advanced handler setup — when wiring pyclifer logging into an existing logging config:

```python
from pyclifer import (
    RichExtraFormatter,
    RichExtraStreamHandler,
    add_trace_method,
    TRACE,
)
import logging

# Add .trace() method to any logger
logger = logging.getLogger("myapp")
add_trace_method(logger)
logger.trace("low-level trace message")  # level 5

# Build a handler manually
handler = RichExtraStreamHandler()
handler.setFormatter(RichExtraFormatter())
handler.setLevel(TRACE)
```

Most projects use `configure_rich_logging()` or `@app_group(use_rich_logging=True)` instead —
these primitives are for custom setups.
```

- [ ] **Step 4: Verify build**

```bash
mkdocs build --strict 2>&1 | grep -E "WARNING|ERROR"
```

Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add docs/logging.md
git commit -m "📝 docs(logging): list full DEFAULT_FIELDS, add PYCLIFER_LOG_LEVELS value, add_trace_method example"
```

---

## Task 5: Document BaseRenderer ClassVar defaults in output-formatting.md [MINOR]

**Files:**
- Modify: `docs/output-formatting.md:262-340` (BaseRenderer section)

Three ClassVars with no user-facing docs:
- `model_class: ClassVar[type[BaseModel] | None] = None` — alternative to `fields` for Pydantic/dataclass models
- `datetime_format: ClassVar[str] = "%Y-%m-%d %H:%M"`
- `date_format: ClassVar[str] = "%Y-%m-%d"`

- [ ] **Step 1: Add model_class note to the Declarative renderer example**

In `docs/output-formatting.md`, in the `### Declarative renderer` section (after the `ArticleRenderer` example, around line 285), add:

```markdown
If your model is a dataclass or Pydantic model, set `model_class` instead of listing `fields`
manually — the framework derives the field list from the model's field names:

```python
from pyclifer import BaseRenderer, BaseModel


class Article(BaseModel):
    id: str
    title: str
    author: str
    published: str


class ArticleRenderer(BaseRenderer):
    model_class = Article  # fields derived automatically: ["id", "title", "author", "published"]
    columns = ["id", "title", "author"]
    rich_title = "Articles"
```

`model_class` is a shorthand — explicit `fields` always takes precedence if both are set.
```

- [ ] **Step 2: Add datetime_format and date_format note**

In `docs/output-formatting.md`, after the `model_class` note, add:

```markdown
#### Date formatting in tables

`table()` formats `datetime` and `date` values using:

- `datetime_format = "%Y-%m-%d %H:%M"` (default)
- `date_format = "%Y-%m-%d"` (default)

Override per-renderer:

```python
class EventRenderer(BaseRenderer):
    fields = ["id", "name", "starts_at"]
    datetime_format = "%d/%m/%Y %H:%M"  # European style
```
```

- [ ] **Step 3: Verify build**

```bash
mkdocs build --strict 2>&1 | grep -E "WARNING|ERROR"
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add docs/output-formatting.md
git commit -m "📝 docs(output-formatting): document model_class, datetime_format, date_format on BaseRenderer"
```

---

## Self-Review

**Spec coverage:**
- ✅ CRITICAL getting-started Step 3 → Task 1
- ✅ MODERATE Response pattern → Task 2
- ✅ MODERATE `option(store_in_meta)` → Task 3
- ✅ MODERATE `DEFAULT_FIELDS` full list → Task 4
- ✅ MINOR `command(handle_response)` → Task 3
- ✅ MINOR `app_group(auto_envvar_prefix, rich_help_config, use_rich_help)` → Task 3
- ✅ MINOR `PYCLIFER_LOG_LEVELS` value → Task 4
- ✅ MINOR `add_trace_method`, `RichExtraFormatter`, `RichExtraStreamHandler` → Task 4
- ✅ MINOR `BaseRenderer.model_class` → Task 5
- ✅ MINOR `BaseRenderer.datetime_format`, `date_format` → Task 5
- ⚠️ MINOR "Click re-exports reference" — omitted intentionally: adding a full re-exports table is additive scope, not a fix. Can be a separate spec item.

**Placeholder scan:** No TBD/TODO/similar. Code blocks are complete.

**Type consistency:** No cross-task type references (doc-only changes).