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

## BaseRenderer

Declarative base class for all pyclif output renderers. Subclass and set class
attributes (`fields`, `columns`, `rich_title`, `success_message`, `failure_message`)
to control every output format without overriding methods.

::: pyclif.BaseRenderer

---

## ResponseRenderer

Protocol that all renderer implementations must satisfy. Implement this Protocol
directly only when inheriting `BaseRenderer` is not appropriate.

::: pyclif.ResponseRenderer