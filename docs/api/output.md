# Output

## OperationResult

The atomic result type returned by interface methods. Carries success state, an item
identifier, a message, optional data payload, and an error code.

::: pyclif.OperationResult

---

## Response

The standard return type for all pyclif commands. Carries success state, a human-readable
message, optional structured data, and an error code.

::: pyclif.Response

---

## CliTable

Wrapper around Rich `Table` for consistent tabular output.

::: pyclif.CliTable

---

## CliTableColumn

Column definition for `CliTable`.

::: pyclif.CliTableColumn

---

## ExceptionTable

Renders an exception as a Rich table. Used internally by the response formatter but
available for direct use in error handlers.

::: pyclif.ExceptionTable

---

## Output formats

| Format  | Output                                          | Filterable |
|---------|-------------------------------------------------|------------|
| `json`  | Syntax-highlighted JSON                         | yes        |
| `yaml`  | Syntax-highlighted YAML                         | yes        |
| `table` | Rich table                                      | no         |
| `rich`  | Live / panels / markdown                        | no         |
| `raw`   | Flat JSON, no highlighting — machine-readable   | yes        |
| `text`  | Plain text: `response.message` only             | no         |

`table` is the default format. `raw` is the machine-readable format for scripting
— use it with `--output-filter` or pipe to `jq`.

`--output-filter` extracts a single key from the serialized dict. It works with
`raw`, `json`, and `yaml`. When a filter is active on `json` or `yaml`, the
extracted value is printed without syntax highlighting.

---

## BaseRenderer

Declarative base class for all pyclif output renderers. Subclass and set class
attributes (`fields`, `columns`, `rich_title`, `success_message`, `failure_message`)
to control every output format without overriding methods.

Key hooks:

- `text(response)` — returns `response.message` as plain text (used by `--output-format text`)
- `raw(response)` — returns a serialized dict for machine-readable output (used by `--output-format raw`)
- `serialize(response)` — returns a JSON-serializable dict (used by `json`, `yaml`, and `raw`)

::: pyclif.BaseRenderer

---

## ResponseRenderer

Protocol that all renderer implementations must satisfy. Implement this Protocol
directly only when inheriting `BaseRenderer` is not appropriate.

::: pyclif.ResponseRenderer