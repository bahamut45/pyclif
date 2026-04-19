"""pyclif project init <name>."""

from pathlib import Path

from pyclif import Choice, Response, argument, command, option, pass_context

from ..interfaces import ScaffoldingInterface


@command()
@argument("name")
@option(
    "--integrations",
    default="",
    help="Comma-separated integrations to scaffold (e.g. github,docker,slack).",
)
@option(
    "--package-manager",
    type=Choice(["uv", "poetry"], case_sensitive=False),
    default="uv",
    show_default=True,
    help="Package manager to target.",
)
@pass_context
def init(ctx, name: str, integrations: str, package_manager: str) -> Response:
    """Create a new pyclif project skeleton."""
    interface = ScaffoldingInterface(ctx)
    created = interface.init_project(name, package_manager=package_manager)

    if integrations:
        scoped = ScaffoldingInterface(ctx, root=Path(name))
        for integration in [i.strip() for i in integrations.split(",") if i.strip()]:
            created += scoped.add_integration(integration)

    return Response(
        success=True,
        message=f"Project '{name}' created.",
        data={"files": created},
    )
