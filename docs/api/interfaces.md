# Interfaces

## BaseInterface

Base class for the pyclif service layer. Subclass it to group all data-access and
business-logic operations for a resource. Declare a `renderers` dict to associate
each method with its renderer, then call `respond()` from commands — it handles list
vs generator detection, renderer selection, and `Response` construction automatically.

::: pyclif.BaseInterface
