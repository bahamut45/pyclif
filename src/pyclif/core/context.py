"""Context class"""

import sys

from rich.console import Console

from pyclif.core.mixins import OutputFormatMixin, RichHelpersMixin


class ContextException(Exception):
    """Base exception for context-specific errors in the application."""


class BaseContext(RichHelpersMixin, OutputFormatMixin):
    """BaseContext class initializes state and combines output and rich helpers for CLI commands."""

    def __init__(self):
        """Initialize the context with a console and detect TTY mode."""
        self.console = Console()
        self.is_atty = sys.stdout.isatty()
        self.output_format = None
