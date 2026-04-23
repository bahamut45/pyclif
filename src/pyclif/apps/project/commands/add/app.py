"""pyclif project add app <name>."""

from pyclif import Response, argument, command, option, pass_context

from ...interfaces import ScaffoldingInterface


@command()
@argument("name")
@option(
    "--no-group",
    "flat",
    is_flag=True,
    default=False,
    help="Expose commands directly on the root app without a @group layer.",
)
@pass_context
def app(ctx, name: str, flat: bool) -> Response:
    """Add an app to the current project."""
    return ScaffoldingInterface(ctx).respond("add_app", name, flat=flat)
