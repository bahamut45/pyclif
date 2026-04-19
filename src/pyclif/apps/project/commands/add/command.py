"""pyclif project add command <name> --app <app>."""

from pyclif import argument, command, option, pass_context, Response

from ...interfaces import ScaffoldingInterface
from ...tables import ScaffoldingTable


@command()
@argument("name")
@option("--app", "app_name", required=True, help="App that owns this command.")
@pass_context
def command_(ctx, name: str, app_name: str) -> Response:
    """Add a command to an existing app."""
    interface = ScaffoldingInterface(ctx)
    created = interface.add_command(name, app_name)
    return Response(
        success=True,
        message=f"Command '{name}' added to app '{app_name}'.",
        data={"files": created},
        callback_table_output=ScaffoldingTable,
    )
