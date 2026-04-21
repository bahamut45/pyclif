"""pyclif project add app <name>."""

from pyclif import Response, argument, command, pass_context

from ...interfaces import ScaffoldingInterface


@command()
@argument("name")
@pass_context
def app(ctx, name: str) -> Response:
    """Add an app to the current project."""
    return ScaffoldingInterface(ctx).respond("add_app", name)
