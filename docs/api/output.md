# Output

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