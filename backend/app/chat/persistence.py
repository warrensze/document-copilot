from __future__ import annotations

import uuid

import psycopg

from app.assistant.outputs import Citation
from app.config import settings


def _dsn() -> str:
    return settings.database_url.replace("+psycopg", "")


def _get_conn():
    return psycopg.connect(_dsn())


def ensure_user(owner_id: str, email: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO users (id, email) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            (owner_id, email),
        )
        conn.commit()


def get_or_create_thread(thread_id: str, owner_id: str, email: str) -> dict:
    ensure_user(owner_id, email)
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, owner_id, title FROM chat_threads WHERE id = %s",
            (thread_id,),
        ).fetchone()
        if row:
            return {"id": str(row[0]), "owner_id": str(row[1]), "title": row[2]}

        conn.execute(
            "INSERT INTO chat_threads (id, owner_id) VALUES (%s, %s)",
            (thread_id, owner_id),
        )
        conn.commit()
        return {"id": thread_id, "owner_id": owner_id, "title": None}


def save_user_message(thread_id: str, content: str, message_id: str) -> str:
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, thread_id, role, content) VALUES (%s, %s, 'user', %s)",
            (message_id, thread_id, content),
        )
        conn.execute(
            "UPDATE chat_threads SET updated_at = now() WHERE id = %s",
            (thread_id,),
        )
        conn.commit()
    return message_id


def save_assistant_message(
    thread_id: str,
    content: str,
    citations: list[Citation],
    meta: dict | None = None,
) -> str:
    msg_id = str(uuid.uuid4())
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, thread_id, role, content, meta) VALUES (%s, %s, 'assistant', %s, %s)",
            (msg_id, thread_id, content, meta or {}),
        )
        for c in citations:
            conn.execute(
                "INSERT INTO message_citations (message_id, chunk_id, excerpt) VALUES (%s, %s, %s)",
                (msg_id, c.chunk_id, c.excerpt),
            )
        conn.execute(
            "UPDATE chat_threads SET updated_at = now() WHERE id = %s",
            (thread_id,),
        )
        conn.commit()
    return msg_id


def set_thread_title(thread_id: str, title: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "UPDATE chat_threads SET title = COALESCE(title, %s), updated_at = now() WHERE id = %s",
            (title, thread_id),
        )
        conn.commit()


def list_threads(owner_id: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT id, title, created_at, updated_at
               FROM chat_threads
               WHERE owner_id = %s
               ORDER BY updated_at DESC""",
            (owner_id,),
        ).fetchall()
        return [
            {
                "id": str(r[0]),
                "title": r[1] or "",
                "created_at": r[2].isoformat() if r[2] else None,
                "updated_at": r[3].isoformat() if r[3] else None,
            }
            for r in rows
        ]


def get_thread_messages(thread_id: str, owner_id: str) -> list[dict] | None:
    with _get_conn() as conn:
        thread = conn.execute(
            "SELECT id FROM chat_threads WHERE id = %s AND owner_id = %s",
            (thread_id, owner_id),
        ).fetchone()
        if not thread:
            return None

        rows = conn.execute(
            """SELECT id, role, content, meta, created_at
               FROM chat_messages
               WHERE thread_id = %s
               ORDER BY created_at ASC""",
            (thread_id,),
        ).fetchall()

        messages = []
        for r in rows:
            msg: dict = {
                "id": str(r[0]),
                "role": r[1],
                "content": r[2],
                "meta": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
            }
            if r[1] == "assistant":
                cites = conn.execute(
                    "SELECT chunk_id, excerpt FROM message_citations WHERE message_id = %s",
                    (str(r[0]),),
                ).fetchall()
                msg["citations"] = [
                    {"chunk_id": str(c[0]), "excerpt": c[1]} for c in cites
                ]
            messages.append(msg)
        return messages


def auto_title(user_message: str) -> str:
    text = user_message.strip().split("\n")[0]
    if len(text) > 50:
        text = text[:47] + "..."
    return text
