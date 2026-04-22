# Project Scaffolding

pyclif ships a built-in `project` command that generates Django-inspired project structures so
you can skip the boilerplate and start writing business logic immediately.

```bash
pyclif project --help
pyclif project add --help
```

## Creating a new project

```bash
pyclif project init my-project
```

This creates a fully wired `my-project/` directory with a `src/` layout, a test suite, a
`pyproject.toml`, and a `.gitignore`.

**Options**

| Option | Default | Description |
|---|---|---|
| `--package-manager` | `uv` | Toolchain to target — `uv` or `poetry` |
| `--integrations` | _(none)_ | Comma-separated integrations to scaffold in one shot |

```bash
# Target poetry instead of uv
pyclif project init my-project --package-manager poetry

# Generate a project and immediately scaffold two integrations
pyclif project init my-project --integrations github,slack
```

### Generated structure

```
my-project/
├── pyproject.toml              # build system, scripts, bumpversion config
├── README.md
├── .gitignore
├── src/my_project/
│   ├── __init__.py
│   ├── cli.py                  # @app_group entry point, wires all app groups
│   ├── core/
│   │   ├── context.py          # MyProjectContext(BaseContext) + pass_cli_context
│   │   ├── constants.py
│   │   ├── options.py
│   │   └── integrations/
│   │       └── __init__.py
│   └── apps/
│       └── __init__.py         # groups = [] — add_app appends here
└── tests/
    ├── __init__.py
    └── conftest.py
```

The generated `cli.py` wires groups dynamically so each new app you add is picked up
automatically:

```python
from pyclif import app_group
from .core.context import MyProjectContext
from .apps import groups

@app_group(handle_response=True, output_format_default="json")
@click.pass_context
def app(ctx):
    """MyProject CLI."""
    ctx.obj = MyProjectContext()

for group in groups:
    app.add_command(group)
```

## Adding an app

An _app_ is a self-contained feature area — a Click group with its own commands, interfaces,
models, and tables.

```bash
# Run from the project root
pyclif project add app users
```

**What gets created**

```
src/my_project/apps/users/
├── __init__.py         # @group() decorator + add_command loop
├── interfaces.py       # UsersInterface + UsersRenderer stubs
├── models.py
├── tables.py
└── commands/
    └── __init__.py     # commands = []
```

**What gets wired**

`apps/__init__.py` is updated automatically:

```python
from .users import users
groups.append(users)
```

## Adding a command

A _command_ belongs to an existing app. It gets its own file and is immediately reachable on
the CLI.

```bash
pyclif project add command list --app users
```

**Options**

| Option | Required | Description |
|---|---|---|
| `--app` | yes | App that owns this command |

**What gets created**

```
src/my_project/apps/users/commands/list.py
```

```python
from pyclif import command, Response
from ....core.context import pass_cli_context
from ..interfaces import UsersInterface

@command()
@pass_cli_context
def list(ctx) -> Response:
    """List description."""
    return UsersInterface(ctx).respond("list_items")
```

**What gets wired**

`apps/users/commands/__init__.py` is updated automatically:

```python
from .list import list
commands.append(list)
```

## Adding an integration

An _integration_ wraps an external library or service and is attached to the application
context so every command can access it via `ctx`.

```bash
# Single-file integration
pyclif project add integration github

# Package integration (client + helpers + models)
pyclif project add integration github --package
```

**Options**

| Option | Default | Description |
|---|---|---|
| `--package` | off | Generate a package with `client.py`, `helpers.py`, and `models.py` |

**Single-file layout**

```
src/my_project/core/integrations/github.py
```

```python
class GithubIntegration:
    """Integration for Github."""

    def __init__(self):
        pass
```

**Package layout**

```
src/my_project/core/integrations/github/
├── __init__.py     # exposes GithubIntegration, wires GithubClient
├── client.py       # GithubClient stub
├── helpers.py
└── models.py
```

**What gets wired**

`core/context.py` is updated in two places — an import is injected after the existing imports,
and `__init__` gets the instance assigned:

```python
from .integrations.github import GithubIntegration   # ← injected

class MyProjectContext(BaseContext):
    def __init__(self):
        super().__init__()
        self.github = GithubIntegration()             # ← injected
```

Every command with a typed context can then reach the integration via `ctx.github`.

## Name conventions

All scaffolding commands accept names in either `kebab-case` or `snake_case`. pyclif derives
the other variants automatically:

| Input | `name_snake` | `name_pascal` |
|---|---|---|
| `my-project` | `my_project` | `MyProject` |
| `user_profile` | `user_profile` | `UserProfile` |
| `github` | `github` | `Github` |

## Error handling

- **Directory already exists** (`init`): exits with code 2 rather than overwriting.
- **App not found** (`add command`): suggests running `add app` first.
- **File already exists** (any command): exits with code 2; no file is touched.
- **`src/` not found** (`add app`, `add command`, `add integration`): reports that the
  current directory is not a pyclif project root.

## Typical workflow

```bash
# 1. Bootstrap
pyclif project init my-project
cd my-project
uv sync --dev

# 2. Add a feature area
pyclif project add app users

# 3. Add commands to it
pyclif project add command list  --app users
pyclif project add command get   --app users
pyclif project add command create --app users

# 4. Wrap an external service
pyclif project add integration github --package

# 5. Run the CLI
uv run my-project --help
uv run my-project users list
```