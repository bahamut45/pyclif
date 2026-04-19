"""pyclif project add integration <name>."""

from pyclif import argument, command, option, pass_context, Response

from ...interfaces import ScaffoldingInterface
from ...tables import ErrorTable, ScaffoldingTable


@command()
@argument("name")
@option("--package", is_flag=True, default=False, help="Generate a package instead of a single file.")
@pass_context
def integration(ctx, name: str, package: bool) -> Response:
    """Add an integration to the current project."""
    try:
        interface = ScaffoldingInterface(ctx)
        created = interface.add_integration(name, package=package)
        return Response(
            success=True,
            message=f"Integration '{name}' created.",
            data={"files": created},
            callback_table_output=ScaffoldingTable,
        )
    except (FileExistsError, FileNotFoundError) as e:
        return Response(success=False, message=str(e), error_code=1, callback_table_output=ErrorTable)
