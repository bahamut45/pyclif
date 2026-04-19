# Core Classes

Internal Click subclasses and configuration objects. Exposed publicly for advanced use
cases such as subclassing or type-checking.

## PyclifOption

Extends `click.Option` with `is_global` and env-var binding support.

::: pyclif.PyclifOption

---

## PyclifGroup

Base Click group class used by `app_group` and `group`. Composes
`HandleResponseMixin` + `GlobalOptionsMixin`.

::: pyclif.PyclifGroup

---

## CustomConfigOption

Extends click-extra's config option with multi-location Linux config file search
(`/etc/<app>/`, `~/.config/<app>/`, etc.).

::: pyclif.CustomConfigOption