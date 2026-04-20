"""pyclif project add app <name>."""

from pyclif import Response, argument, command, pass_context

from ...interfaces import ScaffoldingInterface
from ...tables import ScaffoldingTable


@command()
@argument("name")
@pass_context
def app(ctx, name: str) -> Response:
    """Add an app to the current project."""
    return Response.from_results(
        ScaffoldingInterface(ctx).add_app(name),
        success_message=f"App '{name}' created.",
        failure_message=f"App '{name}' creation failed.",
        table=ScaffoldingTable,
    )
