"""Tests for pyclifer.testing — CliResult and invoke() helper."""

import pytest

from pyclifer import Response, app_group, echo, pass_context, returns_response
from pyclifer.testing import CliResult, invoke


def make_cli(output_format: str = "json"):
    # handle_response=False: hello is decorated with @returns_response explicitly,
    # and fail must raise uncaught so the exception reaches CliResult.exception.
    @app_group(
        add_version_option=False,
        output_format_default=output_format,
        handle_response=False,
    )
    @pass_context
    def cli(ctx):
        pass

    @cli.command()
    @returns_response
    @pass_context
    def hello(ctx):
        return Response(success=True, message="hello world", data={"key": "value"})

    @cli.command()
    @pass_context
    def fail(ctx):
        raise RuntimeError("boom")

    return cli


class TestCliResult:
    """CliResult wraps Click's Result with typed accessors."""

    def test_exit_code_zero_on_success(self):
        cli = make_cli()
        result = invoke(cli, ["hello"])
        assert result.exit_code == 0

    def test_output_contains_stdout(self):
        cli = make_cli("text")
        result = invoke(cli, ["hello"])
        assert "hello world" in result.output

    def test_json_parses_json_output(self):
        cli = make_cli("json")
        result = invoke(cli, ["hello"])
        assert result.json["success"] is True
        assert result.json["message"] == "hello world"
        assert result.json["data"]["key"] == "value"

    def test_yaml_parses_yaml_output(self):
        cli = make_cli("yaml")
        result = invoke(cli, ["hello"])
        assert result.yaml["success"] is True

    def test_json_raises_value_error_on_non_json(self):
        cli = make_cli("text")
        result = invoke(cli, ["hello"])
        with pytest.raises(ValueError, match="output is not valid JSON"):
            _ = result.json

    def test_yaml_raises_value_error_on_non_yaml(self):
        @app_group(add_version_option=False)
        @pass_context
        def cli(ctx):
            pass

        @cli.command()
        def bad():
            echo("{unbalanced")

        result = invoke(cli, ["bad"])
        with pytest.raises(ValueError, match="output is not valid YAML"):
            _ = result.yaml

    def test_stderr_captures_output_written_to_stderr(self):
        @app_group(add_version_option=False)
        @pass_context
        def cli(ctx):
            pass

        @cli.command()
        def warn():
            echo("careful now", err=True)

        result = invoke(cli, ["warn"])
        assert "careful now" in result.stderr
        assert "careful now" not in result.output

    def test_exception_is_none_on_success(self):
        cli = make_cli()
        result = invoke(cli, ["hello"])
        assert result.exception is None

    def test_exception_captured_on_failure(self):
        cli = make_cli()
        result = invoke(cli, ["fail"], catch_exceptions=True)
        assert result.exception is not None
        assert isinstance(result.exception, RuntimeError)


class TestInvokeHelper:
    """invoke() wraps CliRunner with sensible defaults."""

    def test_invoke_returns_cli_result(self):
        cli = make_cli()
        result = invoke(cli, ["hello"])
        assert isinstance(result, CliResult)

    def test_invoke_with_env(self):
        cli = make_cli()
        result = invoke(cli, ["hello"], env={"SOME_VAR": "1"})
        assert result.exit_code == 0

    def test_invoke_with_input(self):
        @app_group(add_version_option=False)
        @pass_context
        def cli(ctx):
            pass

        @cli.command()
        def ask():
            val = input("Enter: ")
            print(f"Got: {val}")

        result = invoke(cli, ["ask"], input="hello\n")
        assert "Got: hello" in result.output

    def test_invoke_catch_exceptions_false_propagates(self):
        cli = make_cli()
        with pytest.raises(RuntimeError, match="boom"):
            invoke(cli, ["fail"], catch_exceptions=False)


class TestPytestFixtures:
    """pytest fixtures from pyclifer.testing are importable and functional."""

    def test_cli_runner_fixture_returns_a_runner(self, cli_runner):
        from click.testing import CliRunner

        assert isinstance(cli_runner, CliRunner)

    def test_cli_invoke_fixture_invokes_a_command(self, cli_invoke):
        cli = make_cli()
        result = cli_invoke(cli, ["hello"])
        assert isinstance(result, CliResult)
        assert result.exit_code == 0
