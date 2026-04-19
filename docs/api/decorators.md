# Decorators

The four main decorators are the public surface of pyclif. They wrap Click objects with
framework features: automatic configuration, global option propagation, Rich logging, and
standardized response handling.

## app_group

Entry point decorator. Creates the root CLI group with all framework features enabled.

::: pyclif.app_group

---

## group

Creates a subgroup that inherits global options from its parent.

::: pyclif.group

---

## command

Creates a CLI command. Use inside a group or app_group.

::: pyclif.command

---

## option

Extends Click options with environment variable binding and optional global propagation.

::: pyclif.option

---

## output_filter_option

Adds `--output-format` to a command (JSON, YAML, Table, Rich, Raw).

::: pyclif.output_filter_option

---

## returns_response

Decorator that intercepts a `Response` return value and dispatches it to the formatter.
Applied automatically when `handle_response=True` on `@app_group`.

::: pyclif.returns_response