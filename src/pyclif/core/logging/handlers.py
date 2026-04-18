"""Rich handlers for pyclif logging."""

import sys
import logging
from rich.console import Console
from rich.logging import RichHandler
from click_extra.logging import ExtraStreamHandler

from .filters import SecretsMasker
from .levels import TRACE, add_trace_method


class RichExtraStreamHandler(ExtraStreamHandler):
    """Enhanced ExtraStreamHandler with Rich support and built-in security filtering.

    Extends click-extra's ExtraStreamHandler to use Rich for beautiful logging
    while maintaining compatibility with click.echo() and color support.
    Automatically includes SecretsMasker for sensitive data protection.
    """

    def __init__(
        self,
        stream=None,
        rich_tracebacks=True,
        enable_secrets_filter=True,
        **kwargs,
    ):
        """Initialize the Rich Extra Stream Handler.

        Args:
            stream: Output stream (defaults to sys.stderr).
            rich_tracebacks: Enable Rich tracebacks.
            enable_secrets_filter: Enable automatic secrets filtering.
            **kwargs: Additional keyword arguments passed to RichHandler.
        """
        # Initialize the parent ExtraStreamHandler
        super().__init__(stream or sys.stderr)

        # Create Rich console that uses the same stream
        self.rich_console = Console(
            file=self.stream,
            stderr=(self.stream == sys.stderr),
        )

        # Create Rich handler for advanced features
        self._rich_handler = RichHandler(
            console=self.rich_console,
            rich_tracebacks=rich_tracebacks,
            **kwargs,
        )

        # Add secrets filter by default
        if enable_secrets_filter:
            self.addFilter(SecretsMasker())

    def emit(self, record):
        """Use Rich handler for enhanced output while maintaining click-extra compatibility.

        Args:
            record: LogRecord to emit.
        """
        try:
            # Use Rich handler's emit method for better formatting
            self._rich_handler.emit(record)
        except RecursionError:
            raise
        except Exception:
            # Fallback to parent's behavior
            super().emit(record)