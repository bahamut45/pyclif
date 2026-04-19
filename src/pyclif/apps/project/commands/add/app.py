"""pyclif project add app <name>."""

from pyclif import argument, command, pass_context, Response

from ...interfaces import ScaffoldingInterface
from ...tables import ScaffoldingTable


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
        callback_table_output=ScaffoldingTable,
    )
