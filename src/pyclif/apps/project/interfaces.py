"""File system operations and template rendering for project scaffolding."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


class ScaffoldingInterface:
    """Renders templates and manages generated project files.

    Args:
        ctx: The CLI context (unused at this layer, kept for pyclif convention).
        root: Project root directory. Defaults to the current working directory.
    """

    _TEMPLATES_DIR = Path(__file__).parent / "templates"

    def __init__(self, ctx, root: Path = Path(".")) -> None:
        self.ctx = ctx
        self._root = root
        self._env = Environment(
            loader=FileSystemLoader(str(self._TEMPLATES_DIR)),
            keep_trailing_newline=True,
        )

    def init_project(self, name: str, package_manager: str = "uv") -> list[dict[str, str]]:
        """Create a full project skeleton in a new directory.

        Args:
            name: Project name (kebab-case or snake_case).
            package_manager: Toolchain to target — "uv" (default) or "poetry".

        Returns:
            Paths of all files created, relative to the new project root.

        Raises:
            FileExistsError: If the target directory already exists.
            ValueError: If package_manager is not supported.
        """
        if package_manager not in ("uv", "poetry"):
            raise ValueError(
                f"Unsupported package manager '{package_manager}'. Use 'uv' or 'poetry'."
            )

        ns = self._names(name)
        root = Path(name)
        if root.exists():
            raise FileExistsError(f"Directory '{name}' already exists.")

        pkg = f"src/{ns['name_snake']}"
        pm_tmpl = f"pyproject_{package_manager}.toml.jinja2"
        files = [
            (root / "pyproject.toml", pm_tmpl),
            (root / "README.md", "readme.md.jinja2"),
            (root / ".gitignore", "gitignore.jinja2"),
            (root / f"{pkg}/__init__.py", "project_package_init.py.jinja2"),
            (root / f"{pkg}/cli.py", "project_cli.py.jinja2"),
            (root / f"{pkg}/core/context.py", "project_context.py.jinja2"),
            (root / f"{pkg}/core/constants.py", "project_constants.py.jinja2"),
            (root / f"{pkg}/core/options.py", "project_options.py.jinja2"),
            (root / f"{pkg}/core/integrations/__init__.py", "project_integrations_init.py.jinja2"),
            (root / f"{pkg}/apps/__init__.py", "project_apps_init.py.jinja2"),
            (root / "tests/__init__.py", "tests_init.py.jinja2"),
            (root / "tests/conftest.py", "tests_conftest.py.jinja2"),
        ]
        return [p for dest, tmpl in files for p in self._write_rendered(dest, tmpl, ns)]

    def add_app(self, name: str) -> list[dict[str, str]]:
        """Create an app skeleton inside the current project's apps/ directory.

        Args:
            name: App name (snake_case).

        Returns:
            Paths of all files created or modified.

        Raises:
            FileExistsError: If the app directory already exists.
            FileNotFoundError: If apps/__init__.py is not found (not a project root).
        """
        ns = self._names(name)
        app_dir = self._root / "src" / self._detect_package() / "apps" / ns["name_snake"]
        if app_dir.exists():
            raise FileExistsError(f"App '{name}' already exists at {app_dir}.")

        files = [
            (app_dir / "__init__.py", "app_init.py.jinja2"),
            (app_dir / "interfaces.py", "app_interfaces.py.jinja2"),
            (app_dir / "models.py", "app_models.py.jinja2"),
            (app_dir / "tables.py", "app_tables.py.jinja2"),
            (app_dir / "commands/__init__.py", "app_commands_init.py.jinja2"),
        ]
        created = [p for dest, tmpl in files for p in self._write_rendered(dest, tmpl, ns)]
        return created + self._wire_app(ns["name_snake"])

    def add_command(self, name: str, app: str) -> list[dict[str, str]]:
        """Create a command file inside an app's commands/ directory.

        Args:
            name: Command name (snake_case).
            app: App name to add the command to.

        Returns:
            Paths of all files created or modified.

        Raises:
            FileExistsError: If the command file already exists.
            FileNotFoundError: If the target app does not exist.
        """
        ns = self._names(name)
        pkg = self._detect_package()
        commands_dir = self._root / "src" / pkg / "apps" / app / "commands"
        if not commands_dir.exists():
            raise FileNotFoundError(
                f"App '{app}' not found. Run `pyclif project add app {app}` first."
            )
        cmd_file = commands_dir / f"{ns['name_snake']}.py"
        if cmd_file.exists():
            raise FileExistsError(f"Command '{name}' already exists at {cmd_file}.")

        return self._write_rendered(cmd_file, "command.py.jinja2", ns) + self._wire_command(
            ns["name_snake"], app
        )

    def add_integration(self, name: str, package: bool = False) -> list[dict[str, str]]:
        """Create an integration module inside core/integrations/.

        Args:
            name: Integration name (snake_case).
            package: When True, generate a package with a client, helpers, models.

        Returns:
            Paths of all files created or modified.

        Raises:
            FileExistsError: If the integration already exists.
            FileNotFoundError: If core/integrations/ is not found.
        """
        ns = self._names(name)
        pkg = self._detect_package()
        integrations_dir = self._root / "src" / pkg / "core" / "integrations"
        if not integrations_dir.exists():
            raise FileNotFoundError(
                "core/integrations/ not found. Are you in a pyclif project root?"
            )

        if package:
            pkg_dir = integrations_dir / ns["name_snake"]
            if pkg_dir.exists():
                raise FileExistsError(f"Integration '{name}' already exists at {pkg_dir}.")
            files = [
                (pkg_dir / "__init__.py", "integration_package_init.py.jinja2"),
                (pkg_dir / "client.py", "integration_package_client.py.jinja2"),
                (pkg_dir / "helpers.py", "integration_package_helpers.py.jinja2"),
                (pkg_dir / "models.py", "integration_package_models.py.jinja2"),
            ]
            created = [p for dest, tmpl in files for p in self._write_rendered(dest, tmpl, ns)]
        else:
            simple_file = integrations_dir / f"{ns['name_snake']}.py"
            if simple_file.exists():
                raise FileExistsError(f"Integration '{name}' already exists at {simple_file}.")
            created = self._write_rendered(simple_file, "integration_simple.py.jinja2", ns)

        return created + self._wire_integration(ns["name_snake"], ns["name_pascal"])

    def _wire_app(self, name_snake: str) -> list[dict[str, str]]:
        """Append import and groups.append call to apps/__init__.py.

        Args:
            name_snake: Snake-case app name.

        Returns:
            List containing the path of the modified file.
        """
        pkg = self._detect_package()
        apps_init = self._root / "src" / pkg / "apps" / "__init__.py"
        self._append_to_file(
            apps_init,
            f"\nfrom .{name_snake} import {name_snake}\ngroups.append({name_snake})\n",
        )
        return [{"file": str(apps_init), "action": "modified"}]

    def _wire_command(self, name_snake: str, app: str) -> list[dict[str, str]]:
        """Append import and commands.append call to the app's commands/__init__.py.

        Args:
            name_snake: Snake-case command name.
            app: App name that owns this command.

        Returns:
            List containing the path of the modified file.
        """
        pkg = self._detect_package()
        commands_init = self._root / "src" / pkg / "apps" / app / "commands" / "__init__.py"
        self._append_to_file(
            commands_init,
            f"\nfrom .{name_snake} import {name_snake}\ncommands.append({name_snake})\n",
        )
        return [{"file": str(commands_init), "action": "modified"}]

    def _wire_integration(self, name_snake: str, name_pascal: str) -> list[dict[str, str]]:
        """Inject an integration import and property stub into core/context.py.

        Args:
            name_snake: Snake-case integration name.
            name_pascal: PascalCase integration name.

        Returns:
            List containing the path of the modified file.
        """
        pkg = self._detect_package()
        context_file = self._root / "src" / pkg / "core" / "context.py"
        content = context_file.read_text()

        new_import = f"from .integrations.{name_snake} import {name_pascal}Integration\n"
        content = re.sub(
            r"((?:^(?:from|import)[^\n]+\n)+)",
            lambda m: m.group(0) + new_import,
            content,
            count=1,
            flags=re.MULTILINE,
        )
        content = content.replace(
            "        super().__init__()\n",
            f"        super().__init__()\n        self.{name_snake} = {name_pascal}Integration()\n",
            1,
        )
        context_file.write_text(content)
        return [{"file": str(context_file), "action": "modified"}]

    def _render(self, template_name: str, variables: dict) -> str:
        """Render a Jinja2 template with the given variables.

        Args:
            template_name: Filename inside the templates/ directory.
            variables: Template context variables.

        Returns:
            Rendered string content.
        """
        return self._env.get_template(template_name).render(**variables)

    def _write_rendered(
        self, path: Path, template_name: str, variables: dict
    ) -> list[dict[str, str]]:
        """Render a template and write it to disk.

        Args:
            path: Destination file path.
            template_name: Template to render.
            variables: Template context variables.

        Returns:
            Single-element list with the stringified path.

        Raises:
            FileExistsError: If the destination file already exists.
        """
        if path.exists():
            raise FileExistsError(f"File '{path}' already exists.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._render(template_name, variables))
        return [{"file": str(path), "action": "created"}]

    @staticmethod
    def _append_to_file(path: Path, content: str) -> None:
        """Append content to an existing file.

        Args:
            path: File to append to.
            content: Text to append.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"File '{path}' not found.")
        with path.open("a") as fh:
            fh.write(content)

    @staticmethod
    def _names(name: str) -> dict[str, str]:
        """Derive snake_case and PascalCase variants from a name.

        Args:
            name: Raw name (kebab-case or snake_case).

        Returns:
            Dict with keys: name, name_snake, name_pascal.
        """
        snake = name.replace("-", "_")
        pascal = "".join(word.capitalize() for word in snake.split("_"))
        return {"name": name, "name_snake": snake, "name_pascal": pascal}

    def _detect_package(self) -> str:
        """Detect the Python package name from the src/ directory.

        Returns:
            The package directory name found under src/.

        Raises:
            FileNotFoundError: If src/ does not exist or contains no package.
        """
        src = self._root / "src"
        if not src.exists():
            raise FileNotFoundError("src/ directory not found. Are you in a pyclif project root?")
        candidates = [d for d in src.iterdir() if d.is_dir() and not d.name.startswith(".")]
        if not candidates:
            raise FileNotFoundError("No package found under src/.")
        return candidates[0].name
