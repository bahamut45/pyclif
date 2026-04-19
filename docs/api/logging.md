# Logging

pyclif ships a Rich-enhanced logging system with a custom `TRACE` level (5), automatic
secrets masking, and rotating file handler support.

## get_logger

Main factory. Returns a logger pre-configured with Rich formatting.

::: pyclif.get_logger

---

## get_configured_logger

Returns a logger with full configuration applied (handlers, level, masker).

::: pyclif.get_configured_logger

---

## configure_rich_logging

Low-level setup function. Called internally by `get_configured_logger`.

::: pyclif.configure_rich_logging

---

## add_trace_method

Patches a logger instance with a `.trace()` method at level 5.

::: pyclif.add_trace_method

---

## SecretsMasker

Log filter that redacts sensitive values from log records.

::: pyclif.SecretsMasker

---

## RichExtraFormatter / RichExtraStreamHandler

Rich-aware formatter and stream handler. Wired up automatically by `configure_rich_logging`.

::: pyclif.RichExtraFormatter

::: pyclif.RichExtraStreamHandler

---

## Constants

::: pyclif.TRACE

::: pyclif.PYCLIF_LOG_LEVELS