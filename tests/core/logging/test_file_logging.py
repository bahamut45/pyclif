"""Unit tests for time-based rotating file logging configuration."""

import logging
from logging.handlers import TimedRotatingFileHandler

import pytest
from click.testing import CliRunner

from pyclif.core.decorators import app_group
from pyclif.core.logging.config import setup_file_logging


@pytest.fixture(autouse=True)
def clean_logging():
    """Fixture to clean up logging handlers after each test.

    Ensures that file handlers don't leak between tests and files are closed
    properly to avoid permission errors during temp directory cleanup.
    """
    yield
    root_logger = logging.getLogger()
    click_extra_logger = logging.getLogger("click_extra")

    for logger in [root_logger, click_extra_logger]:
        for handler in list(logger.handlers):
            if isinstance(handler, TimedRotatingFileHandler):
                logger.removeHandler(handler)
                handler.close()


def test_setup_file_logging(tmp_path):
    """Test that setup_file_logging adds the correct handler and writes to the file."""
    log_file = tmp_path / "test.log"

    # noinspection PyArgumentEqualDefault
    setup_file_logging(str(log_file), level="DEBUG", enable_secrets_filter=True)

    root_logger = logging.getLogger()
    file_handlers = [h for h in root_logger.handlers if isinstance(h, TimedRotatingFileHandler)]

    assert len(file_handlers) == 1

    root_logger.warning("Test log message")

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Test log message" in content
    assert "WARNING" in content


def test_setup_file_logging_idempotency(tmp_path):
    """Test that calling setup_file_logging multiple times doesn't duplicate handlers."""
    log_file = tmp_path / "test_idempotent.log"

    setup_file_logging(str(log_file), level="DEBUG")
    setup_file_logging(str(log_file), level="DEBUG")

    root_logger = logging.getLogger()
    file_handlers = [h for h in root_logger.handlers if isinstance(h, TimedRotatingFileHandler)]

    assert len(file_handlers) == 1


# noinspection PyTypeChecker
def test_cli_log_file_option(tmp_path):
    """Test the --log-file CLI option integration and secret masking."""

    @app_group()
    def cli():
        """Dummy CLI."""
        pass

    @cli.command()
    def do_work():
        """Dummy command."""
        logger = logging.getLogger("test_cli")
        logger.warning({"action": "Executing work", "token": "SECRET_TOKEN_123"})

    runner = CliRunner()
    log_file = tmp_path / "cli_output.log"

    result = runner.invoke(cli, ["--log-file", str(log_file), "do-work"])

    assert result.exit_code == 0
    assert log_file.exists()

    content = log_file.read_text(encoding="utf-8")
    assert "Executing work" in content
    assert "'token': '*CENSORED*'" in content
    assert "SECRET_TOKEN_123" not in content


# noinspection PyTypeChecker,PyUnusedLocal
def test_cli_log_file_level_decorator(tmp_path):
    """Test that the log file captures the correct level defined via decorator."""

    @app_group(log_file_default_level="INFO")
    def cli():
        """Dummy CLI."""
        pass

    @cli.command()
    def do_work():
        """Dummy command."""
        logger = logging.getLogger("test_cli")
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")

    runner = CliRunner()
    log_file = tmp_path / "cli_level.log"

    result = runner.invoke(cli, ["--log-file", str(log_file), "do-work"])

    assert result.exit_code == 0
    assert log_file.exists()

    content = log_file.read_text(encoding="utf-8")
    assert "Warning message" in content
    assert "Info message" in content
    assert "Debug message" not in content
