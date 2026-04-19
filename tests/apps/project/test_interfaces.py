"""Unit tests for ScaffoldingInterface."""

import pytest

from pyclif.apps.project.interfaces import ScaffoldingInterface


@pytest.fixture
def iface(tmp_path):
    """ScaffoldingInterface rooted at tmp_path."""
    return ScaffoldingInterface(ctx=None, root=tmp_path)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A freshly initialised project in tmp_path."""
    monkeypatch.chdir(tmp_path)
    iface = ScaffoldingInterface(ctx=None)
    iface.init_project("my-app")
    return ScaffoldingInterface(ctx=None, root=tmp_path / "my-app")


class TestNames:
    """Test suite for the _names helper."""

    def test_kebab_case(self) -> None:
        """Convert kebab-case to snake and pascal variants."""
        result = ScaffoldingInterface._names("ship-cli")
        assert result == {"name": "ship-cli", "name_snake": "ship_cli", "name_pascal": "ShipCli"}

    def test_snake_case(self) -> None:
        """Snake-case input passes through unchanged."""
        result = ScaffoldingInterface._names("my_app")
        assert result == {"name": "my_app", "name_snake": "my_app", "name_pascal": "MyApp"}

    def test_single_word(self) -> None:
        """Single word produces identical snake and lowercase pascal."""
        result = ScaffoldingInterface._names("github")
        assert result == {"name": "github", "name_snake": "github", "name_pascal": "Github"}


class TestInitProject:
    """Test suite for init_project."""

    def test_creates_expected_files(self, tmp_path, monkeypatch) -> None:
        """All project skeleton files are written."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        created = iface.init_project("my-app")
        paths = {r["file"] for r in created}

        assert any("pyproject.toml" in p for p in paths)
        assert any("cli.py" in p for p in paths)
        assert any("context.py" in p for p in paths)
        assert any("conftest.py" in p for p in paths)

    def test_all_actions_are_created(self, tmp_path, monkeypatch) -> None:
        """init_project only creates files — no modified entries."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        created = iface.init_project("my-app")
        assert all(r["action"] == "created" for r in created)

    def test_raises_if_directory_exists(self, tmp_path, monkeypatch) -> None:
        """Second init with the same name raises FileExistsError."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        iface.init_project("my-app")
        with pytest.raises(FileExistsError, match="already exists"):
            iface.init_project("my-app")

    def test_uv_pyproject(self, tmp_path, monkeypatch) -> None:
        """uv template includes hatchling build backend."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        iface.init_project("my-app", package_manager="uv")
        content = (tmp_path / "my-app" / "pyproject.toml").read_text()
        assert "hatchling" in content
        assert "dependency-groups" in content

    def test_poetry_pyproject(self, tmp_path, monkeypatch) -> None:
        """poetry template includes poetry build backend."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        iface.init_project("my-app", package_manager="poetry")
        content = (tmp_path / "my-app" / "pyproject.toml").read_text()
        assert "poetry-core" in content
        assert "tool.poetry" in content

    def test_invalid_package_manager(self, tmp_path, monkeypatch) -> None:
        """Unsupported package manager raises ValueError."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        with pytest.raises(ValueError, match="Unsupported package manager"):
            iface.init_project("my-app", package_manager="pipenv")


class TestAddApp:
    """Test suite for add_app."""

    def test_creates_app_files(self, project) -> None:
        """App skeleton files are written under apps/."""
        created = project.add_app("repos")
        paths = {r["file"] for r in created}

        assert any("repos/__init__.py" in p for p in paths)
        assert any("repos/interfaces.py" in p for p in paths)
        assert any("repos/models.py" in p for p in paths)
        assert any("repos/tables.py" in p for p in paths)
        assert any("repos/commands/__init__.py" in p for p in paths)

    def test_wires_app_in_apps_init(self, project, tmp_path) -> None:
        """apps/__init__.py is updated with the new group import."""
        project.add_app("repos")
        content = (tmp_path / "my-app" / "src" / "my_app" / "apps" / "__init__.py").read_text()
        assert "from .repos import repos" in content
        assert "groups.append(repos)" in content

    def test_modified_action_for_apps_init(self, project) -> None:
        """The apps/__init__.py entry is marked as modified."""
        results = project.add_app("repos")
        modified = [r for r in results if r["action"] == "modified"]
        assert len(modified) == 1
        assert "__init__.py" in modified[0]["file"]

    def test_raises_if_app_exists(self, project) -> None:
        """Second add_app with same name raises FileExistsError."""
        project.add_app("repos")
        with pytest.raises(FileExistsError, match="already exists"):
            project.add_app("repos")


class TestAddCommand:
    """Test suite for add_command."""

    def test_creates_command_file(self, project) -> None:
        """Command file is written inside the app's commands/ directory."""
        project.add_app("repos")
        created = project.add_command("list", "repos")
        assert any("commands/list.py" in r["file"] for r in created)

    def test_wires_command_in_commands_init(self, project, tmp_path) -> None:
        """commands/__init__.py is updated with the new command import."""
        project.add_app("repos")
        project.add_command("list", "repos")
        path = (
            tmp_path / "my-app" / "src" / "my_app" / "apps" / "repos" / "commands" / "__init__.py"
        )
        content = path.read_text()
        assert "from .list import list" in content
        assert "commands.append(list)" in content

    def test_raises_if_app_not_found(self, project) -> None:
        """add_command raises FileNotFoundError when the app does not exist."""
        with pytest.raises(FileNotFoundError, match="App 'unknown' not found"):
            project.add_command("list", "unknown")

    def test_raises_if_command_exists(self, project) -> None:
        """Second add_command with the same name raises FileExistsError."""
        project.add_app("repos")
        project.add_command("list", "repos")
        with pytest.raises(FileExistsError, match="already exists"):
            project.add_command("list", "repos")


class TestAddIntegration:
    """Test suite for add_integration."""

    def test_creates_simple_integration(self, project) -> None:
        """Simple integration writes a single .py file."""
        created = project.add_integration("github")
        assert any("integrations/github.py" in r["file"] for r in created)

    def test_creates_package_integration(self, project) -> None:
        """Package integration writes client, helpers, models and __init__."""
        created = project.add_integration("ssh", package=True)
        paths = {r["file"] for r in created}
        assert any("ssh/__init__.py" in p for p in paths)
        assert any("ssh/client.py" in p for p in paths)
        assert any("ssh/helpers.py" in p for p in paths)
        assert any("ssh/models.py" in p for p in paths)

    def test_wires_integration_in_context(self, project, tmp_path) -> None:
        """core/context.py receives import and property stub."""
        project.add_integration("github")
        content = (tmp_path / "my-app" / "src" / "my_app" / "core" / "context.py").read_text()
        assert "from .integrations.github import GithubIntegration" in content
        assert "self.github = GithubIntegration()" in content

    def test_raises_if_integration_exists(self, project) -> None:
        """Second add_integration with the same name raises FileExistsError."""
        project.add_integration("github")
        with pytest.raises(FileExistsError, match="already exists"):
            project.add_integration("github")
