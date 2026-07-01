from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest
from psycopg.types.json import Jsonb

from app.chat.persistence import (
    auto_title,
    ensure_user,
    get_or_create_thread,
    get_thread_messages,
    list_threads,
    save_assistant_message,
    save_user_message,
    set_thread_title,
)
from app.assistant.outputs import Citation


@pytest.fixture(autouse=True)
def _mock_db_url(monkeypatch):
    monkeypatch.setattr("app.chat.persistence.settings.database_url", "postgresql://localhost:5432/test")


def _make_row(values):
    row = MagicMock()
    row.__getitem__.side_effect = lambda i: values[i]
    return row


@pytest.fixture
def db():
    conn = MagicMock()
    conn.commit = MagicMock()
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    conn.execute = MagicMock()
    with patch("app.chat.persistence._get_conn", return_value=conn):
        yield conn


class TestEnsureUser:
    def test_inserts_user(self, db):
        ensure_user("u-1", "a@b.com")
        db.execute.assert_called_once_with(
            "INSERT INTO users (id, email) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            ("u-1", "a@b.com"),
        )

    def test_conflict_does_not_raise(self, db):
        db.execute.side_effect = [None, None]
        ensure_user("u-1", "a@b.com")
        db.execute.assert_called_once()


class TestGetOrCreateThread:
    def test_creates_new_thread_when_not_found(self, db):
        db.execute.return_value.fetchone.return_value = None

        result = get_or_create_thread("t-1", "u-1", "a@b.com")

        assert result["id"] == "t-1"
        assert db.execute.call_count == 3

    def test_returns_existing_thread(self, db):
        now = datetime.now(timezone.utc)
        db.execute.return_value.fetchone.return_value = _make_row(("t-1", "u-1", "Existing"))

        result = get_or_create_thread("t-1", "u-1", "a@b.com")

        assert result["title"] == "Existing"
        assert db.execute.call_count == 2


class TestSaveUserMessage:
    def test_inserts_message(self, db):
        save_user_message("t-1", "hello", "m-1")
        calls = [
            call(
                "INSERT INTO chat_messages (id, thread_id, role, content) VALUES (%s, %s, 'user', %s)",
                ("m-1", "t-1", "hello"),
            ),
            call("UPDATE chat_threads SET updated_at = now() WHERE id = %s", ("t-1",)),
        ]
        db.execute.assert_has_calls(calls)

    def test_returns_message_id(self, db):
        msg_id = save_user_message("t-1", "hello", "m-1")
        assert msg_id == "m-1"


class TestSaveAssistantMessage:
    def test_inserts_message_with_citations(self, db):
        citations = [
            Citation(chunk_id="c-1", excerpt="Revenue grew 10%", ticker="AAPL", company_name="Apple", year="2025"),
            Citation(chunk_id="c-2", excerpt="Net income $95B", ticker="AAPL", company_name="Apple", year="2025"),
        ]
        msg_id = save_assistant_message("t-1", "Answer text.", citations)

        assert isinstance(msg_id, str)

        insert_call = db.execute.call_args_list[0]
        sql, params = insert_call[0]
        assert "INSERT INTO chat_messages" in sql
        assert params[2] == "Answer text."

    def test_inserts_citation_rows(self, db):
        citations = [Citation(chunk_id="c-1", excerpt="Excerpt text", ticker="AAPL", company_name="Apple", year="2025")]
        save_assistant_message("t-1", "text", citations)

        citation_call = db.execute.call_args_list[1]
        sql, params = citation_call[0]
        assert "INSERT INTO message_citations" in sql
        assert params[1] == "c-1"
        assert params[2] == "Excerpt text"

    def test_updates_thread_timestamp(self, db):
        save_assistant_message("t-1", "text", [])

        last_call = db.execute.call_args_list[-1]
        sql, params = last_call[0]
        assert "UPDATE chat_threads" in sql
        assert params == ("t-1",)

    def test_returns_uuid_string(self, db):
        msg_id = save_assistant_message("t-1", "text", [])
        assert isinstance(msg_id, str)
        assert len(msg_id) == 36


class TestAssistantMessageMetaWrapped:
    """Verify meta dict is wrapped in Jsonb() to prevent 'cannot adapt type dict'."""

    def test_meta_dict_is_jsonb_wrapped(self, db):
        save_assistant_message("t-1", "text", [], meta={"source": "test"})
        params = db.execute.call_args_list[0][0][1]
        assert isinstance(params[3], Jsonb)
        assert params[3].obj == {"source": "test"}

    def test_meta_none_becomes_empty_jsonb(self, db):
        save_assistant_message("t-1", "text", [], meta=None)
        params = db.execute.call_args_list[0][0][1]
        assert isinstance(params[3], Jsonb)
        assert params[3].obj == {}


class TestListThreads:
    def test_returns_empty_list(self, db):
        db.execute.return_value.fetchall.return_value = []

        result = list_threads("u-1")
        assert result == []

    def test_returns_parsed_threads(self, db):
        now = datetime.now(timezone.utc)
        db.execute.return_value.fetchall.return_value = [
            _make_row(("t-1", "Title 1", now, now)),
            _make_row(("t-2", None, now, now)),
        ]

        result = list_threads("u-1")

        assert result[0]["title"] == "Title 1"
        assert result[1]["title"] == ""
        assert result[0]["id"] == "t-1"
        assert "created_at" in result[0]
        assert "updated_at" in result[0]

    def test_queries_by_owner(self, db):
        db.execute.return_value.fetchall.return_value = []
        list_threads("u-42")
        sql = db.execute.call_args[0][0]
        assert "owner_id" in sql


class TestGetThreadMessages:
    def test_returns_none_for_nonexistent_thread(self, db):
        db.execute.return_value.fetchone.return_value = None
        assert get_thread_messages("t-fake", "u-1") is None

    def test_parses_user_messages(self, db):
        now = datetime.now(timezone.utc)
        db.execute.return_value.fetchone.return_value = _make_row(("t-1",))
        db.execute.return_value.fetchall.side_effect = [
            [_make_row(("m-1", "user", "hello", None, now))],
            [],
        ]

        msgs = get_thread_messages("t-1", "u-1")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "hello"
        assert "citations" not in msgs[0]

    def test_parses_assistant_messages_with_citations(self, db):
        now = datetime.now(timezone.utc)
        db.execute.return_value.fetchone.return_value = _make_row(("t-1",))
        db.execute.return_value.fetchall.side_effect = [
            [_make_row(("m-1", "assistant", "Answer", {"key": "val"}, now))],
            [_make_row(("c-1", "Excerpt text"))],
        ]

        msgs = get_thread_messages("t-1", "u-1")
        assert len(msgs) == 1
        assert msgs[0]["meta"] == {"key": "val"}
        assert len(msgs[0]["citations"]) == 1
        assert msgs[0]["citations"][0]["chunk_id"] == "c-1"


class TestSetThreadTitle:
    def test_updates_title(self, db):
        set_thread_title("t-1", "New Title")
        db.execute.assert_called_once_with(
            "UPDATE chat_threads SET title = COALESCE(title, %s), updated_at = now() WHERE id = %s",
            ("New Title", "t-1"),
        )


class TestAutoTitle:
    def test_uses_first_line(self):
        assert auto_title("Hello world") == "Hello world"

    def test_truncates_long_lines(self):
        long = "a" * 60
        assert auto_title(long) == "a" * 47 + "..."

    def test_strips_whitespace(self):
        assert auto_title("  hello  ") == "hello"

    def test_empty_input(self):
        assert auto_title("") == ""
