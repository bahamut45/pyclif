"""pyclif project init <name>."""

from pathlib import Path

from pyclif import Choice, Response, argument, command, option, pass_context

from ..interfaces import ScaffoldingInterface
from ..tables import ScaffoldingTable


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
    results = interface.init_project(name, package_manager=package_manager)

    if all(r.success for r in results) and integrations:
        scoped = ScaffoldingInterface(ctx, root=Path(name))
        for integration in [i.strip() for i in integrations.split(",") if i.strip()]:
            results += scoped.add_integration(integration)

    return Response.from_results(
        results,
        success_message=f"Project '{name}' created.",
        failure_message=f"Project '{name}' creation failed.",
        table=ScaffoldingTable,
    )
