"""pyclif project add integration <name>."""

from pyclif import Response, argument, command, option, pass_context

from ...interfaces import ScaffoldingInterface
from ...tables import ScaffoldingTable


@command()
@argument("name")
@option(
    "--package", is_flag=True, default=False, help="Generate a package instead of a single file."
)
@pass_context
def integration(ctx, name: str, package: bool) -> Response:
    """Add an integration to the current project."""
    return Response.from_results(
        ScaffoldingInterface(ctx).add_integration(name, package=package),
        success_message=f"Integration '{name}' created.",
        failure_message=f"Integration '{name}' creation failed.",
        table=ScaffoldingTable,
    )
