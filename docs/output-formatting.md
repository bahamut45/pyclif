# Output Formatting and Responses

pyclif provides a built-in system to standardize and format CLI output. It supports JSON, YAML, interactive
tables, Rich text, and raw values — all powered by `BaseContext` and the `Response` dataclass.

## Core Concepts

The output system is built around three parts:

1. **`BaseContext`** — Combines `OutputFormatMixin` and `RichHelpersMixin`. All commands receive it as their
   Click context and use it to dispatch output.
2. **`Response`** — A standardized dataclass for structuring command results.
3. **Mixins** — `OutputFormatMixin` handles format dispatch; `RichHelpersMixin` provides Rich console helpers.

## Automatic Output Format Option

`@app_group` and `@group` automatically add `--output-format` / `-o` to the CLI. It is propagated globally to
all subcommands. The selected format is stored in `ctx.meta['pyclif.output_format']` and read automatically by
`BaseContext` — you do not need to declare an `output_format` parameter in your functions.

## Automatic Response Dispatch

pyclif provides three complementary mechanisms to print a `Response` automatically when a command returns one,
without manually calling `ctx.print_response(response)`.

### Level 1 — App-wide: `@app_group(handle_response=True)`

```python
from pyclif.core import app_group, option
from pyclif.core.output import Response
import click


@app_group(handle_response=True)
@click.pass_context
def app(ctx):
    """My CLI."""
    pass


@app.command()
@option("--name", default="world")
@click.pass_context
def hello(ctx, name):
    """Greet someone."""
    return Response(success=True, message=f"Hello {name}!", data={"name": name})
```

Per-command override:

```python
@app.command(handle_response=False)
@click.pass_context
def raw_cmd(ctx):
    """This command manages its own output."""
    click.echo("custom output")
```

### Level 2 — Standalone command: `@command(handle_response=True)`

```python
from pyclif.core import command, option
from pyclif.core.output import Response
import click


@command(handle_response=True)
@option("--name", default="world")
@click.pass_context
def hello(ctx, name):
    """Greet someone."""
    return Response(success=True, message=f"Hello {name}!", data={"name": name})


app.add_command(hello)
```

### Level 3 — Explicit decorator: `@returns_response`

```python
from pyclif.core import returns_response
from pyclif.core.output import Response
import click


@app.command()
@returns_response
@click.pass_context
def hello(ctx):
    """Greet someone."""
    return Response(success=True, message="Hello!", data={})
```

### Output Format Resolution

All three mechanisms read the format from `ctx.meta['pyclif.output_format']`, set by `--output-format`.
Explicit values (command-line or environment variable) always take precedence.

```bash
myapp --output-format json hello --name Alice   # JSON output
myapp -o yaml hello                             # YAML output
```

### Missing Callbacks

When `table` or `rich` format is selected but the `Response` has no `callback_table_output` /
`callback_rich_output`, the error is rendered using `ExceptionTable` — consistent with the chosen format.

## Filtering Raw Output — `@output_filter_option()`

Add `@output_filter_option()` to expose `--output-filter` / `-f`, which extracts a single key from the
response payload. Most useful with `raw` format for scripting and pipelines.

```python
from pyclif.core import app_group, output_filter_option, returns_response
from pyclif.core.output import Response
import click


@app_group(handle_response=True, output_format_default="raw")
@click.pass_context
def app(ctx):
    """My CLI."""
    pass


@app.command()
@output_filter_option()
@click.pass_context
def status(ctx):
    """Show service status."""
    return Response(
        success=True,
        message="Service is running",
        data={"service": "api", "status": "running", "uptime": "3d"},
    )
```

```bash
myapp status                          # full dict
myapp status --output-filter status   # running
myapp status -f uptime                # 3d
MYAPP_OUTPUT_FILTER=service myapp status  # api
```

The filter looks first inside `data`, then falls back to top-level response fields (`success`, `message`,
`error_code`).

## The Response Object

```python
from pyclif.core.output import Response

# Basic response
response = Response(
    success=True,
    message="Operation completed successfully",
    data={"id": 1, "status": "active"}
)

# Response with custom table formatting
def format_my_table(resp):
    from pyclif.core.output import CliTable, CliTableColumn
    fields = {
        "id": CliTableColumn(header="ID"),
        "status": CliTableColumn(header="Status"),
    }
    return CliTable(fields=fields, rows=[resp.data])

response_with_table = Response(
    success=True,
    message="Data retrieved",
    data={"id": 1, "status": "active"},
    callback_table_output=format_my_table
)
```

## BaseContext and Mixins

```python
import click
from pyclif.core import app_group
from pyclif.core.context import BaseContext
from pyclif.core.output import Response


@app_group()
@click.pass_context
def cli(ctx):
    """CLI with output management."""
    pass


@cli.command()
@click.pass_context
def get_users(ctx):
    """List users."""
    response = Response(
        success=True,
        message="Users retrieved",
        data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    )
    ctx.print_response(response)
```

## Supported Formats

| Format  | Description                                                                    |
|---------|--------------------------------------------------------------------------------|
| `json`  | Response serialized as formatted JSON                                          |
| `yaml`  | Response serialized as YAML with syntax highlighting                           |
| `table` | Rich CLI table — uses `callback_table_output` if provided                      |
| `rich`  | Rich rendering — uses `callback_rich_output` if provided                       |
| `raw`   | Response serialized to dict and printed; supports key filtering                |

### Error Handling

```python
@cli.command()
@click.pass_context
def risky_command(ctx):
    """A command that may fail."""
    try:
        raise ValueError("Connection timeout")
    except Exception as e:
        ctx.print_error(e)
```

Depending on the output format, this renders a clean JSON/YAML error or a formatted `ExceptionTable`.

## Rich Helpers

`RichHelpersMixin` (included in `BaseContext`) gives easy access to Rich console interactions:

```python
@cli.command()
@click.pass_context
def interactive_command(ctx):
    """Interactive command."""
    ctx.rich_panel("Welcome to interactive mode!", title="Hello")

    name = ctx.ask_user("What is your name?", default="User")

    with ctx.show_status("Processing..."):
        import time
        time.sleep(2)
```

## Table Utilities

pyclif provides built-in table components:

- **`CliTable`**: Pre-styled Rich table for structured data.
- **`CliTableColumn`**: Column descriptor with header, style, and justify options.
- **`ExceptionTable`**: Specialized table for displaying formatted exception details.

```python
from pyclif.core.output import CliTable, CliTableColumn

fields = {
    "id": CliTableColumn(header="ID", justify="right"),
    "name": CliTableColumn(header="Name"),
    "active": CliTableColumn(header="Active"),
}

table = CliTable(fields=fields, rows=[
    {"id": 1, "name": "Alice", "active": True},
    {"id": 2, "name": "Bob", "active": False},
])
```

## See Also

- [Getting Started](getting-started.md)
- [Examples](examples.md)
- [Configuration Management](configuration.md)
