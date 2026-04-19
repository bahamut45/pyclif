"""Unit tests for the RichHelpersMixin."""

from unittest.mock import MagicMock, patch

from rich.panel import Panel

from pyclif.core.mixins.rich import RichHelpersMixin


class DummyRichContext(RichHelpersMixin):
    """Dummy context class to test the RichHelpersMixin.

    Provides the required 'console' attribute mock.
    """

    def __init__(self) -> None:
        """Initialize the dummy context with a mocked console."""
        self.console = MagicMock()


class TestRichHelpersMixin:
    """Test suite for the RichHelpersMixin class."""

    def test_rich_panel_creation_and_print(self) -> None:
        """Test that rich_panel creates a Panel and prints it if requested."""
        context = DummyRichContext()

        panel = context.rich_panel(text="Test content", title="Test Title", console_print=True)

        assert isinstance(panel, Panel)
        assert panel.renderable == "Test content"
        assert panel.title == "Test Title"

        context.console.print.assert_called_once_with(panel)

    @patch("pyclif.core.mixins.rich.Rule")
    def test_display_rule(self, mock_rule_class: MagicMock) -> None:
        """Test that display_rule creates a Rule and prints it to the console."""
        context = DummyRichContext()
        mock_rule_instance = MagicMock()
        mock_rule_class.return_value = mock_rule_instance

        context.display_rule(title="Section", style="red")

        mock_rule_class.assert_called_once_with(title="Section", style="red")
        context.console.print.assert_called_once_with(mock_rule_instance)

    def test_show_status(self) -> None:
        """Test that show_status calls the console status method."""
        context = DummyRichContext()

        context.show_status(message="Loading...", spinner="bouncingBar")

        context.console.status.assert_called_once_with("Loading...", spinner="bouncingBar")

    @patch("pyclif.core.mixins.rich.Prompt.ask")
    def test_ask_user(self, mock_prompt_ask: MagicMock) -> None:
        """Test that ask_user correctly wraps the rich Prompt.ask method."""
        context = DummyRichContext()
        mock_prompt_ask.return_value = "user_input"

        result = context.ask_user("Enter name:", default="John", password=True)

        assert result == "user_input"
        mock_prompt_ask.assert_called_once_with(
            "Enter name:",
            default="John",
            choices=None,
            password=True,
            console=context.console,
        )

    @patch("pyclif.core.mixins.rich.Confirm.ask")
    def test_ask_confirmation(self, mock_confirm_ask: MagicMock) -> None:
        """Test that ask_confirmation correctly wraps the rich Confirm.ask method."""
        context = DummyRichContext()
        mock_confirm_ask.return_value = True

        # noinspection PyArgumentEqualDefault
        result = context.ask_confirmation("Are you sure?", default=False)

        assert result is True
        mock_confirm_ask.assert_called_once_with(
            "Are you sure?", default=False, console=context.console
        )
