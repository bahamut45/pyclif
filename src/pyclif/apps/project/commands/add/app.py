"""pyclif project add app <name>."""

from pyclif import Response, argument, command, pass_context

from ...interfaces import ScaffoldingInterface
from ...tables import ErrorTable, ScaffoldingTable


@command()
@argument("name")
@pass_context
def app(ctx, name: str) -> Response:
    """Add an app to the current project."""
    try:
        interface = ScaffoldingInterface(ctx)
        created = interface.add_app(name)
        return Response(
            success=True,
            message=f"App '{name}' created.",
            data={"files": created},
            callback_table_output=ScaffoldingTable,
        )
    except (FileExistsError, FileNotFoundError) as e:
        return Response(
            success=False, message=str(e), error_code=1, callback_table_output=ErrorTable
        )
