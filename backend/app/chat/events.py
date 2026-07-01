from __future__ import annotations

import json


def _json(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def status_event(status: str, detail: str = "") -> str:
    return _json({
        "type": "data-status",
        "data": {"status": status, "detail": detail},
        "transient": True,
    })


def text_start(message_id: str) -> str:
    return _json({"type": "text-start", "id": message_id})


def text_delta(message_id: str, delta: str) -> str:
    return _json({"type": "text-delta", "id": message_id, "delta": delta})


def text_end(message_id: str) -> str:
    return _json({"type": "text-end", "id": message_id})


def citations_event(
    citations: list[dict],
    message_id: str | None = None,
) -> str:
    payload: dict = {
        "type": "data-citations",
        "data": {"citations": citations},
        "transient": True,
    }
    if message_id:
        payload["id"] = message_id
    return _json(payload)


def error_event(error_text: str) -> str:
    return _json({
        "type": "data-error",
        "data": {"errorText": error_text},
        "transient": True,
    })
