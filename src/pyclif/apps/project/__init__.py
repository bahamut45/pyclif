"""Project scaffolding app — `pyclif project` command group."""

from pyclif import group

from .commands import commands


@group()
def project():
    """Scaffold and manage pyclif projects."""


for command in commands:
    project.add_command(command)
