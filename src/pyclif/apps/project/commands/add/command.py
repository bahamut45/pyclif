"""pyclif project add command <name> --app <app>."""

from pyclif import Response, argument, command, option, pass_context

from ...interfaces import ScaffoldingInterface
from ...tables import ScaffoldingTable


@command()
@argument("name")
@option("--app", "app_name", required=True, help="App that owns this command.")
@pass_context
def command_(ctx, name: str, app_name: str) -> Response:
    """Add a command to an existing app."""
    return Response.from_results(
        ScaffoldingInterface(ctx).add_command(name, app_name),
        success_message=f"Command '{name}' added to app '{app_name}'.",
        failure_message=f"Failed to add command '{name}'.",
        table=ScaffoldingTable,
    )
