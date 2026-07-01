from __future__ import annotations

import json
import re

from app.chat.events import (
    citations_event,
    error_event,
    status_event,
    text_delta,
    text_end,
    text_start,
)


def _parse_data(line: str) -> dict:
    """Strip 'data: ' prefix and parse JSON from an SSE line."""
    match = re.match(r"^data: (.+)\n\n$", line)
    assert match, f"not valid SSE: {line!r}"
    return json.loads(match.group(1))


class TestStatusEvent:
    def test_basic(self) -> None:
        out = status_event("generating", "Generating answer...")
        data = _parse_data(out)
        assert data["type"] == "data-status"
        assert data["transient"] is True
        assert data["data"]["status"] == "generating"
        assert data["data"]["detail"] == "Generating answer..."

    def test_empty_detail(self) -> None:
        out = status_event("complete")
        data = _parse_data(out)
        assert data["data"]["detail"] == ""


class TestTextEvents:
    def test_text_start(self) -> None:
        out = text_start("msg-1")
        data = _parse_data(out)
        assert data["type"] == "text-start"
        assert data["id"] == "msg-1"

    def test_text_delta(self) -> None:
        out = text_delta("msg-1", "hello")
        data = _parse_data(out)
        assert data["type"] == "text-delta"
        assert data["id"] == "msg-1"
        assert data["delta"] == "hello"

    def test_text_end(self) -> None:
        out = text_end("msg-1")
        data = _parse_data(out)
        assert data["type"] == "text-end"
        assert data["id"] == "msg-1"


class TestCitationsEvent:
    def test_with_message_id(self) -> None:
        citations = [
            {"chunk_id": "c1", "excerpt": "Revenue grew 10%"},
        ]
        out = citations_event(citations, message_id="msg-1")
        data = _parse_data(out)
        assert data["type"] == "data-citations"
        assert data["transient"] is True
        assert data["data"]["citations"] == citations
        assert data["id"] == "msg-1"

    def test_without_message_id(self) -> None:
        out = citations_event([])
        data = _parse_data(out)
        assert "id" not in data

    def test_multiple_citations(self) -> None:
        citations = [
            {"chunk_id": "c1", "excerpt": "First"},
            {"chunk_id": "c2", "excerpt": "Second"},
        ]
        out = citations_event(citations)
        data = _parse_data(out)
        assert len(data["data"]["citations"]) == 2


class TestErrorEvent:
    def test_basic(self) -> None:
        out = error_event("Something went wrong")
        data = _parse_data(out)
        assert data["type"] == "data-error"
        assert data["transient"] is True
        assert data["data"]["errorText"] == "Something went wrong"

    def test_empty_message(self) -> None:
        out = error_event("")
        data = _parse_data(out)
        assert data["data"]["errorText"] == ""
