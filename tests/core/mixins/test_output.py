"""Unit tests for the OutputFormatMixin."""

import json
from unittest.mock import MagicMock, patch

from pyclif.core.mixins.output import OutputFormatMixin, _ExceptionRenderer
from pyclif.core.output import Response
from pyclif.core.output.renderer import BaseRenderer
from pyclif.core.output.responses import OperationResult


class DummyOutputContext(OutputFormatMixin):
    """Minimal context for testing OutputFormatMixin."""

    def __init__(self, output_format: str | None = "table") -> None:
        """Initialize with a mocked console and specific format.

        Args:
            output_format: The output format to use during dispatch.
        """
        self.console = MagicMock()
        self.output_format = output_format


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(item: str = "a", **data_kwargs) -> OperationResult:
    return OperationResult.ok(item, data=data_kwargs if data_kwargs else None)


def _response_with_renderer(
    results: list[OperationResult] | None = None,
    renderer: BaseRenderer | None = None,
) -> Response:
    if results is None:
        results = [_ok()]
    return Response.from_results(results, renderer=renderer or BaseRenderer())


# ---------------------------------------------------------------------------
# TestPrintErrorBasedOnFormat
# ---------------------------------------------------------------------------


class TestPrintErrorBasedOnFormat:
    """Tests for print_error_based_on_format."""

    def test_creates_response_and_dispatches(self) -> None:
        ctx = DummyOutputContext(output_format="text")
        ctx.print_result_based_on_format = MagicMock()  # type: ignore[method-assign]
        ctx.print_error_based_on_format(ValueError("something went wrong"))
        ctx.print_result_based_on_format.assert_called_once()
        arg = ctx.print_result_based_on_format.call_args[0][0]
        assert isinstance(arg, Response)
        assert arg.success is False
        assert "something went wrong" in arg.message

    def test_renderer_is_exception_renderer(self) -> None:
        ctx = DummyOutputContext(output_format="text")
        ctx.print_result_based_on_format = MagicMock()  # type: ignore[method-assign]
        ctx.print_error_based_on_format(RuntimeError("boom"))
        arg = ctx.print_result_based_on_format.call_args[0][0]
        assert isinstance(arg.renderer, _ExceptionRenderer)

    def test_table_format_uses_exception_renderer_table(self) -> None:
        ctx = DummyOutputContext(output_format="table")
        ctx.print_error_based_on_format(ValueError("oops"))
        ctx.console.print.assert_called_once()


# ---------------------------------------------------------------------------
# TestPrintResultFallbackRenderer
# ---------------------------------------------------------------------------


class TestPrintResultFallbackRenderer:
    """print_result_based_on_format uses BaseRenderer when renderer is None."""

    def test_bare_response_uses_base_renderer(self) -> None:
        ctx = DummyOutputContext(output_format="text")
        response = Response(success=True, message="bare response", renderer=BaseRenderer())
        ctx.print_result_based_on_format(response)
        ctx.console.print.assert_called_once_with("bare response")

    def test_renderer_is_attached_to_response(self) -> None:
        ctx = DummyOutputContext(output_format="table")
        response = Response(success=True, message="ok")
        assert response.renderer is None
        ctx.print_result_based_on_format(response)
        assert isinstance(response.renderer, BaseRenderer)


# ---------------------------------------------------------------------------
# TestPrintRawDict
# ---------------------------------------------------------------------------


class TestPrintRawDict:
    """Tests for _print_raw_dict."""

    def test_no_filter_prints_compact_json(self) -> None:
        ctx = DummyOutputContext()
        data = {"success": True, "message": "ok"}
        ctx._print_raw_dict(data, None)
        args, _ = ctx.console.print.call_args
        parsed = json.loads(args[0])
        assert parsed["success"] is True

    def test_filter_in_data_sub_dict(self) -> None:
        ctx = DummyOutputContext()
        data = {"success": True, "data": {"results": [{"id": 42}]}}
        ctx._print_raw_dict(data, "results")
        ctx.console.print.assert_called_once_with([{"id": 42}])

    def test_filter_at_top_level(self) -> None:
        ctx = DummyOutputContext()
        data = {"success": True, "message": "done", "data": {}}
        ctx._print_raw_dict(data, "message")
        ctx.console.print.assert_called_once_with("done")

    def test_filter_data_takes_priority_over_top_level(self) -> None:
        ctx = DummyOutputContext()
        data = {"message": "top", "data": {"message": "nested"}}
        ctx._print_raw_dict(data, "message")
        ctx.console.print.assert_called_once_with("nested")

    def test_missing_filter_key_returns_none(self) -> None:
        ctx = DummyOutputContext()
        data = {"success": True, "data": {}}
        ctx._print_raw_dict(data, "nonexistent")
        ctx.console.print.assert_called_once_with(None)


# ---------------------------------------------------------------------------
# TestPrintJson
# ---------------------------------------------------------------------------


class TestPrintJson:
    def test_calls_print_json_with_json_string(self) -> None:
        ctx = DummyOutputContext()
        ctx._print_json({"key": "value"})
        ctx.console.print_json.assert_called_once()
        args, _ = ctx.console.print_json.call_args
        parsed = json.loads(args[0])
        assert parsed == {"key": "value"}

    def test_non_serializable_falls_back_gracefully(self) -> None:
        ctx = DummyOutputContext()

        class _Obj:
            __slots__ = ()

            def __str__(self) -> str:
                return "obj"

        ctx._print_json({"x": _Obj()})
        args, _ = ctx.console.print_json.call_args
        parsed = json.loads(args[0])
        assert isinstance(parsed["x"], str)


# ---------------------------------------------------------------------------
# TestPrintYaml
# ---------------------------------------------------------------------------


class TestPrintYaml:
    @patch("pyclif.core.mixins.output.Syntax")
    def test_calls_print_with_syntax(self, mock_syntax: MagicMock) -> None:
        ctx = DummyOutputContext()
        ctx._print_yaml({"name": "Alice"})
        mock_syntax.assert_called_once()
        yaml_content = mock_syntax.call_args[0][0]
        assert "name: Alice" in yaml_content
        ctx.console.print.assert_called_once()


# ---------------------------------------------------------------------------
# TestRendererPathBatchDispatch
# ---------------------------------------------------------------------------


class TestRendererPathBatchDispatch:
    """Dispatch tests for the renderer path in print_result_based_on_format."""

    def _ctx(self, fmt: str | None) -> DummyOutputContext:
        return DummyOutputContext(output_format=fmt)

    def test_text_format_prints_message(self) -> None:
        ctx = self._ctx("text")
        response = _response_with_renderer()
        response.message = "hello"
        ctx.print_result_based_on_format(response)
        ctx.console.print.assert_called_once_with("hello")

    def test_default_format_uses_table(self) -> None:
        ctx = self._ctx(None)
        renderer = MagicMock(spec=BaseRenderer)
        renderer.table.return_value = "table output"
        response = Response.from_results([_ok()], renderer=renderer)
        ctx.print_result_based_on_format(response)
        renderer.table.assert_called_once_with(response)
        ctx.console.print.assert_called_once_with("table output")

    def test_raw_format_prints_compact_json(self) -> None:
        ctx = self._ctx("raw")
        response = _response_with_renderer()
        ctx.print_result_based_on_format(response)
        args, _ = ctx.console.print.call_args
        parsed = json.loads(args[0])
        assert "success" in parsed

    def test_raw_format_with_filter(self) -> None:
        ctx = self._ctx("raw")
        response = _response_with_renderer()
        response.message = "filtered"
        ctx.print_result_based_on_format(response, options={"filter_value": "message"})
        ctx.console.print.assert_called_once_with("filtered")

    def test_table_format_calls_renderer_table(self) -> None:
        ctx = self._ctx("table")
        renderer = MagicMock(spec=BaseRenderer)
        renderer.table.return_value = "table output"
        response = Response.from_results([_ok()], renderer=renderer)
        ctx.print_result_based_on_format(response)
        renderer.table.assert_called_once_with(response)
        ctx.console.print.assert_called_once_with("table output")

    def test_rich_format_calls_renderer_rich(self) -> None:
        ctx = self._ctx("rich")
        renderer = MagicMock(spec=BaseRenderer)
        response = Response.from_results([_ok()], renderer=renderer)
        ctx.print_result_based_on_format(response)
        renderer.rich.assert_called_once_with(response, ctx.console)

    def test_json_format_calls_print_json(self) -> None:
        ctx = self._ctx("json")
        ctx._print_json = MagicMock()  # type: ignore[method-assign]
        response = _response_with_renderer()
        ctx.print_result_based_on_format(response)
        ctx._print_json.assert_called_once()

    def test_yaml_format_calls_print_yaml(self) -> None:
        ctx = self._ctx("yaml")
        ctx._print_yaml = MagicMock()  # type: ignore[method-assign]
        response = _response_with_renderer()
        ctx.print_result_based_on_format(response)
        ctx._print_yaml.assert_called_once()

    def test_json_with_filter_bypasses_highlighting(self) -> None:
        ctx = self._ctx("json")
        ctx._print_json = MagicMock()  # type: ignore[method-assign]
        ctx._print_raw_dict = MagicMock()  # type: ignore[method-assign]
        response = _response_with_renderer()
        ctx.print_result_based_on_format(response, options={"filter_value": "message"})
        ctx._print_raw_dict.assert_called_once()
        ctx._print_json.assert_not_called()

    def test_yaml_with_filter_bypasses_highlighting(self) -> None:
        ctx = self._ctx("yaml")
        ctx._print_yaml = MagicMock()  # type: ignore[method-assign]
        ctx._print_raw_dict = MagicMock()  # type: ignore[method-assign]
        response = _response_with_renderer()
        ctx.print_result_based_on_format(response, options={"filter_value": "message"})
        ctx._print_raw_dict.assert_called_once()
        ctx._print_yaml.assert_not_called()


# ---------------------------------------------------------------------------
# TestRendererPathStreamDispatch
# ---------------------------------------------------------------------------


class TestRendererPathStreamDispatch:
    """Streaming dispatch tests for print_result_based_on_format."""

    def test_non_rich_stream_is_materialised(self) -> None:
        ctx = DummyOutputContext(output_format="text")
        renderer = BaseRenderer()
        gen = iter([_ok("a"), _ok("b")])
        response = Response.from_stream(gen, renderer=renderer)
        ctx.print_result_based_on_format(response)
        assert "stream" not in response.data
        assert "results" in response.data

    def test_rich_stream_calls_live_hooks(self) -> None:
        ctx = DummyOutputContext(output_format="rich")
        renderer = MagicMock(spec=BaseRenderer)
        renderer.rich_setup.return_value = MagicMock()
        items = [_ok("a"), _ok("b")]
        response = Response.from_stream(iter(items), renderer=renderer)

        with patch("pyclif.core.mixins.output.Live") as mock_live:
            mock_live.return_value.__enter__ = MagicMock(return_value=None)
            mock_live.return_value.__exit__ = MagicMock(return_value=False)
            ctx.print_result_based_on_format(response)

        renderer.rich_setup.assert_called_once()
        assert renderer.rich_on_item.call_count == 2
        renderer.rich_summary.assert_called_once()

    def test_non_rich_stream_then_text_dispatch(self) -> None:
        ctx = DummyOutputContext(output_format="text")

        class _MsgRenderer(BaseRenderer):
            success_message = "stream complete"

        response = Response.from_stream(iter([_ok()]), renderer=_MsgRenderer())
        ctx.print_result_based_on_format(response)
        ctx.console.print.assert_called_once_with("stream complete")
