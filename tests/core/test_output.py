"""Unit tests for Response and OperationResult."""

from collections.abc import Iterator

from pyclif.core.output.renderer import BaseRenderer
from pyclif.core.output.responses import NON_SERIALIZABLE_FIELDS, OperationResult, Response

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(item: str = "a", **data_kwargs) -> OperationResult:
    return OperationResult.ok(item, data=data_kwargs if data_kwargs else None)


def _err(item: str = "b", msg: str = "boom", code: int = 1) -> OperationResult:
    return OperationResult.error(item, msg, error_code=code)


def _stream(*items: OperationResult) -> Iterator[OperationResult]:
    yield from items


# ---------------------------------------------------------------------------
# TestOperationResultOk
# ---------------------------------------------------------------------------


class TestOperationResultOk:
    def test_success_is_true(self) -> None:
        r = OperationResult.ok("x")
        assert r.success is True

    def test_item_is_set(self) -> None:
        r = OperationResult.ok("my-file.py")
        assert r.item == "my-file.py"

    def test_error_code_is_zero(self) -> None:
        r = OperationResult.ok("x")
        assert r.error_code == 0

    def test_data_is_attached(self) -> None:
        r = OperationResult.ok("x", data={"action": "created"})
        assert r.data == {"action": "created"}

    def test_message_is_attached(self) -> None:
        r = OperationResult.ok("x", message="done")
        assert r.message == "done"


# ---------------------------------------------------------------------------
# TestOperationResultError
# ---------------------------------------------------------------------------


class TestOperationResultError:
    def test_success_is_false(self) -> None:
        r = OperationResult.error("x", "bad")
        assert r.success is False

    def test_message_is_set(self) -> None:
        r = OperationResult.error("x", "bad input")
        assert r.message == "bad input"

    def test_default_error_code_is_one(self) -> None:
        r = OperationResult.error("x", "bad")
        assert r.error_code == 1

    def test_custom_error_code(self) -> None:
        r = OperationResult.error("x", "not found", error_code=404)
        assert r.error_code == 404


# ---------------------------------------------------------------------------
# TestResponseToJson
# ---------------------------------------------------------------------------


class TestResponseToJson:
    def test_renderer_excluded(self) -> None:
        r = Response(success=True, message="ok", renderer=BaseRenderer())
        assert "renderer" not in r.to_json()

    def test_non_serializable_fields_constant_covers_renderer(self) -> None:
        assert "renderer" in NON_SERIALIZABLE_FIELDS

    def test_success_and_message_present(self) -> None:
        r = Response(success=True, message="hello")
        j = r.to_json()
        assert j["success"] is True
        assert j["message"] == "hello"


# ---------------------------------------------------------------------------
# TestResponseFromResults
# ---------------------------------------------------------------------------


class TestResponseFromResults:
    def test_all_success(self) -> None:
        r = Response.from_results([_ok(), _ok()])
        assert r.success is True
        assert r.error_code is None

    def test_any_failure_marks_response_failed(self) -> None:
        r = Response.from_results([_ok(), _err()])
        assert r.success is False

    def test_error_code_from_first_failure(self) -> None:
        r = Response.from_results([_ok(), _err(code=7), _err(code=3)])
        assert r.error_code == 7

    def test_results_stored_in_data(self) -> None:
        items = [_ok("a"), _ok("b")]
        r = Response.from_results(items)
        assert r.data["results"] == items

    def test_fixed_message_used_when_provided(self) -> None:
        r = Response.from_results([_ok()], message="done")
        assert r.message == "done"

    def test_success_message_used_on_success(self) -> None:
        r = Response.from_results([_ok()], success_message="all good")
        assert r.message == "all good"

    def test_failure_message_used_on_failure(self) -> None:
        r = Response.from_results([_err()], failure_message="oops")
        assert r.message == "oops"

    def test_default_success_message_contains_count(self) -> None:
        r = Response.from_results([_ok(), _ok()])
        assert "2" in r.message

    def test_default_failure_message_contains_fraction(self) -> None:
        r = Response.from_results([_ok(), _err(), _err()])
        assert "2" in r.message
        assert "3" in r.message

    def test_renderer_attached(self) -> None:
        renderer = BaseRenderer()
        r = Response.from_results([_ok()], renderer=renderer)
        assert r.renderer is renderer


# ---------------------------------------------------------------------------
# TestResponseFromStream
# ---------------------------------------------------------------------------


class TestResponseFromStream:
    def test_stream_stored_without_consuming(self) -> None:
        items = [_ok("a"), _ok("b")]
        gen = _stream(*items)
        r = Response.from_stream(gen, renderer=BaseRenderer())
        assert "stream" in r.data
        assert r.data["stream"] is gen

    def test_generator_not_consumed_at_construction(self) -> None:
        consumed = []

        def _gen():
            for item in [_ok("a"), _ok("b")]:
                consumed.append(item)
                yield item

        Response.from_stream(_gen(), renderer=BaseRenderer())
        assert consumed == []

    def test_renderer_attached(self) -> None:
        renderer = BaseRenderer()
        r = Response.from_stream(_stream(_ok()), renderer=renderer)
        assert r.renderer is renderer

    def test_success_and_message_blank_at_construction(self) -> None:
        r = Response.from_stream(_stream(_ok()), renderer=BaseRenderer())
        assert r.message == ""

    def test_results_not_in_data_at_construction(self) -> None:
        r = Response.from_stream(_stream(_ok()), renderer=BaseRenderer())
        assert "results" not in r.data

    def test_renderer_excluded_from_to_json(self) -> None:
        r = Response.from_stream(_stream(_ok()), renderer=BaseRenderer())
        # consume the stream so _serialize_data doesn't choke on a generator
        list(r.data.pop("stream"))
        r.data["results"] = []
        assert "renderer" not in r.to_json()
