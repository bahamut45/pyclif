# Error Handling

pyclif enforces a strict separation between the service layer (interface) and the view layer
(command). This makes error handling consistent, testable, and free of boilerplate.

## The contract

| Layer | Responsibility |
|-------|----------------|
| **Interface** | Executes actions. Returns `OperationResult`. Never raises for expected business failures. |
| **Command** | Thin view. Calls the interface, builds a `Response` from the results. No try/except. |

Exceptions are reserved for programming errors: missing templates, corrupt state, broken
invariants. The last resort handler catches anything that escapes and formats it as a clean
`Response` — stdout is always properly formatted regardless of the error.

## OperationResult

`OperationResult` is the unit of work returned by an interface method. Use the class methods
to construct success or failure outcomes:

```python
from pyclif import OperationResult

# Success
result = OperationResult.ok("src/my_app/cli.py", data={"action": "created"})

# Failure — normalised error code
result = OperationResult.error(
    "src/my_app/cli.py",
    message="File already exists.",
    error_code=2,
)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `success` | `bool` | Whether the action succeeded |
| `item` | `str` | Human-readable identifier (file path, resource name, …) |
| `data` | `Any` | Optional payload (e.g. `{"action": "created"}`) |
| `message` | `str` | Human-readable description of the outcome |
| `error_code` | `int` | Non-zero on failure |

## Response.from_results()

Aggregates a list of `OperationResult` into a single `Response`:

```python
from pyclif import Response

results = interface.do_something()
response = Response.from_results(
    results,
    success_message="Operation completed.",
    failure_message="Operation failed.",
    table=MyTable,
)
```

- `success=True` only if **all** results succeeded
- `error_code` is taken from the first failed result (0 if all passed)
- `data["results"]` carries the full list for table rendering

**Message selection** — in order of precedence:
1. `message` — fixed, used regardless of outcome
2. `success_message` / `failure_message` — selected based on outcome
3. Auto-generated summary (`"N operation(s) completed."` / `"N/M operation(s) failed."`)

## Writing an interface

Interface methods return `OperationResult` — they never raise for expected failures:

```python
from pyclif import OperationResult

class MyInterface:
    def create_resource(self, name: str) -> OperationResult:
        if self._exists(name):
            return OperationResult.error(name, f"'{name}' already exists.", error_code=2)
        self._write(name)
        return OperationResult.ok(name, data={"action": "created"})

    def bulk_create(self, names: list[str]) -> list[OperationResult]:
        return [self.create_resource(name) for name in names]
```

The interface decides whether to stop on the first failure (return early) or continue
collecting results across all items.

## Writing a command

Commands are thin views — they call the interface and build a `Response`:

```python
from pyclif import Response, argument, command, pass_context

from .interfaces import MyInterface
from .tables import MyTable


@command()
@argument("name")
@pass_context
def create(ctx, name: str) -> Response:
    """Create a resource."""
    return Response.from_results(
        MyInterface(ctx).create_resource(name),
        success_message=f"'{name}' created.",
        failure_message=f"Failed to create '{name}'.",
        table=MyTable,
    )
```

## Boundary rule

| Situation | Interface does |
|-----------|----------------|
| Resource already exists | `OperationResult.error` |
| Target not found | `OperationResult.error` |
| Invalid input | `OperationResult.error` |
| Missing required file (framework bug) | `raise RuntimeError` |
| Corrupt template / broken invariant | `raise RuntimeError` |

## Last resort handler

Any exception that escapes the interface and command is caught by the framework before output
is produced. The two streams are always independent:

- **stdout** — a properly formatted `Response(success=False, message=str(e))`, respecting
  `--output-format` (JSON, table, rich, raw)
- **stderr** — traceback via the logging system, visible at the configured verbosity level

The log level for unhandled exceptions is set on `@app_group`:

```python
from pyclif import app_group

@app_group(
    handle_response=True,
    unhandled_exception_log_level="error",   # default — always visible
)
def main():
    """My CLI."""

# Quieter — traceback only with --log-level debug or --log-level trace
@app_group(
    handle_response=True,
    unhandled_exception_log_level="debug",
)
def main():
    """My CLI."""
```

The default is `"error"` so that nothing is silently swallowed in production. Use `"debug"`
when you want clean output for end users and full traces only for developers.