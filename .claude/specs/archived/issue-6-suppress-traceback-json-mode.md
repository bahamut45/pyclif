# Spec: Suppress Rich traceback in JSON/YAML output mode (issue #6)

## Context

When an unhandled exception occurs inside a `returns_response`-wrapped command, pyclifer logs the
full Rich traceback to stderr via `exc_info=True` **regardless of the current output format**.
In JSON/YAML mode this is undesirable: the error is already fully communicated through the
structured response on stdout; the multi-line Rich traceback on stderr is unstructured noise that
breaks log parsers in backend/daemon contexts.

Relevant code path: `decorators.py::returns_response` (lines 547–555) catches the exception and
calls `_log.log(..., exc_info=True)` unconditionally. Both `output_format` and the current log
level (`pyclifer.unhandled_exception_log_level`) are available in the same `meta` dict.

The existing `--verbosity` / `-v` option (TRACE, DEBUG, …) already serves as the diagnostic
escape hatch — no new flag is needed.

## Items

### ✅ 1 — Suppress traceback in structured output modes, restore via verbosity

In `returns_response`, read `output_format` and the **effective logger level** before the
`_log.log()` call.

**Suppression rule**: emit `exc_info=False` (single-line error) when **all** of the following hold:
- `output_format` is `"json"` or `"yaml"`
- The root logger (or `_log`) is **not** at DEBUG or TRACE level (i.e. `_log.isEnabledFor(logging.DEBUG)` is `False`)

When suppressed, append the exception message inline:

```
ERROR  Unhandled exception in command 'my_command': KeyError: 'some_field'
```

**Full traceback** is preserved when either condition breaks:
- `output_format` is not structured (`"table"`, `"rich"`, `"raw"`, …), **or**
- verbosity is DEBUG or TRACE (user explicitly asked for diagnostics via `-v debug` / `-v trace`)

No new option, no new config field.

### ✅ 2 — Tests

Add/extend tests in `tests/core/test_decorators.py`:

- `test_returns_response_suppresses_traceback_in_json_mode` — exception raised in JSON output
  mode at WARNING level → `exc_info=False`, message logged inline with exception text.
- `test_returns_response_keeps_traceback_in_table_mode` — exception in table mode →
  `exc_info=True`.
- `test_returns_response_debug_verbosity_restores_traceback_in_json_mode` — exception in JSON
  mode with logger at DEBUG level → `exc_info=True`.
- `test_returns_response_trace_verbosity_restores_traceback_in_json_mode` — same with TRACE (5).