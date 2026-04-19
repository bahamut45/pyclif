"""pyclif project add app <name>."""

from pyclif import Response, argument, command, pass_context

from ...interfaces import ScaffoldingInterface


@command()
@argument("name")
@pass_context
def app(ctx, name: str) -> Response:
    """Add an app to the current project."""
    interface = ScaffoldingInterface(ctx)
    created = interface.add_app(name)
    return Response(
        success=True,
        message=f"App '{name}' created.",
        data={"files": created},
    )
