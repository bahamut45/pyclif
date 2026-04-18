"""pyclif — PYthon Command Line Interface Framework"""

__app_name__ = "pyclif"
__version__ = "0.0.1"

from .core.classes import CustomConfigOption, PyclifGroup, PyclifOption
from .core.context import BaseContext
from .core.decorators import (
    app_group,
    command,
    group,
    option,
    output_filter_option,
    returns_response,
)
from .core.logging import (
    PYCLIF_LOG_LEVELS,
    TRACE,
    RichExtraFormatter,
    RichExtraStreamHandler,
    SecretsMasker,
    add_trace_method,
    configure_rich_logging,
    get_configured_logger,
    get_logger,
    logger,
)
from .core.mixins import (
    GlobalOptionsMixin,
    HandleResponseMixin,
    OutputFormatMixin,
    RichHelpersMixin,
)
from .core.output import CliTable, CliTableColumn, ExceptionTable, Response

__all__ = [
    "__app_name__",
    "__version__",
    # methods
    "app_group",
    "group",
    "command",
    "option",
    "output_filter_option",
    "returns_response",
    "get_logger",
    "logger",
    "add_trace_method",
    "get_configured_logger",
    "configure_rich_logging",
    # class
    "BaseContext",
    "Response",
    "CliTable",
    "CliTableColumn",
    "ExceptionTable",
    "CustomConfigOption",
    "PyclifGroup",
    "PyclifOption",
    "GlobalOptionsMixin",
    "HandleResponseMixin",
    "OutputFormatMixin",
    "RichHelpersMixin",
    "RichExtraFormatter",
    "RichExtraStreamHandler",
    "SecretsMasker",
    # Constants
    "PYCLIF_LOG_LEVELS",
    "TRACE",
]
