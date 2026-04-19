"""pyclif project add command <name> --app <app>."""

from pyclif import Response, argument, command, option, pass_context

from ...interfaces import ScaffoldingInterface
from ...tables import ErrorTable, ScaffoldingTable


@command()
@argument("name")
@option("--app", "app_name", required=True, help="App that owns this command.")
@pass_context
def command_(ctx, name: str, app_name: str) -> Response:
    """Add a command to an existing app."""
    try:
        interface = ScaffoldingInterface(ctx)
        created = interface.add_command(name, app_name)
        return Response(
            success=True,
            message=f"Command '{name}' added to app '{app_name}'.",
            data={"files": created},
            callback_table_output=ScaffoldingTable,
        )
    except (FileExistsError, FileNotFoundError) as e:
        return Response(
            success=False, message=str(e), error_code=1, callback_table_output=ErrorTable
        )
