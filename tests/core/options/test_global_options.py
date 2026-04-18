"""Test suite for global options propagation within the CLI framework."""

import click
import pytest
from click.testing import CliRunner

from pyclif.core import app_group, command, group, option


@pytest.fixture
def sample_cli():
    """Provide a sample CLI application with a global option for testing.

    Returns:
        click.Group: The configured CLI root command group.
    """

    @app_group()
    @option("--api-key", is_global=True, help="Global API Key for authentication")
    @click.pass_context
    def cli(ctx, api_key):
        """Root command for the application."""
        pass

    @cli.command()
    @click.pass_context
    def fetch_data(ctx, api_key):
        """Subcommand that requires the global option."""
        click.echo(f"Using API Key: {api_key}")

    return cli


class TestGlobalOptionPropagation:
    """Test suite for global options propagation within the CLI framework."""

    def test_global_option_accessible_by_subcommand(self, sample_cli):
        """Ensure that an option marked as global is available to child commands."""
        runner = CliRunner()

        result = runner.invoke(
            sample_cli, ["fetch-data", "--api-key", "secret-key-123"]
        )

        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        assert "Using API Key: secret-key-123" in result.output

    def test_global_option_in_subcommand_help(self, sample_cli):
        """Ensure the global option is displayed in the subcommand's help output."""
        runner = CliRunner()

        result = runner.invoke(sample_cli, ["fetch-data", "--help"])

        print(
            f"\n--- Help Output for fetch-data ---\n{result.output}----------------------------------"
        )

        assert result.exit_code == 0, (
            f"Help command failed with output: {result.output}"
        )
        assert "--api-key" in result.output
        assert "Global API Key for" in result.output

    def test_global_option_with_add_command(self):
        """Ensure global options propagate when commands are registered via add_command."""
        runner = CliRunner()

        @app_group()
        @option("--api-key", is_global=True, help="Global API Key")
        @click.pass_context
        def cli(ctx, api_key):
            """Test app group cli"""
            pass

        @command(name="external-fetch")
        @click.pass_context
        def external_fetch(ctx, api_key):
            """Test command cli"""
            click.echo(f"External API Key: {api_key}")

        cli.add_command(external_fetch)

        result = runner.invoke(cli, ["external-fetch", "--api-key", "secret-456"])

        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        assert "External API Key: secret-456" in result.output

    def test_global_option_propagation_in_nested_groups(self):
        """Ensure global options propagate through multi-level nested groups."""
        runner = CliRunner()

        @app_group()
        @click.pass_context
        def cli(ctx):
            """Test app group cli"""
            pass

        @group(name="subsystem")
        @click.pass_context
        def subsystem(ctx):
            """Test subgroup cli"""
            pass

        @command(name="do-work")
        @click.pass_context
        def do_work(ctx):
            """Test command cli"""
            verbosity = ctx.meta.get("click_extra.verbosity")
            click.echo(f"Work verbosity: {verbosity}")

        subsystem.add_command(do_work)
        cli.add_command(subsystem)

        result = runner.invoke(cli, ["subsystem", "do-work", "--verbosity", "TRACE"])

        print(
            f"\n--- Help Output for do-work ---\n{result.output}----------------------------------"
        )

        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        assert "Work verbosity: TRACE" in result.output
