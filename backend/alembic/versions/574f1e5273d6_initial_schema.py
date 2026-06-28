"""initial schema

Revision ID: 574f1e5273d6
Revises: 
Create Date: 2026-06-26 23:03:59.698144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID


revision: str = '574f1e5273d6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "source_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("form", sa.String(20), nullable=False),
        sa.Column("filing_date", sa.String(10), nullable=False),
        sa.Column("report_date", sa.String(10), nullable=True),
        sa.Column("accession_number", sa.String(50), nullable=False),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("year", sa.String(4), nullable=False),
        sa.Column("content_markdown", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("source_documents.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("section", sa.String(255), nullable=True),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("search_vector", TSVECTOR, nullable=True),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("meta", JSONB, nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "chat_threads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_id", UUID(as_uuid=True), sa.ForeignKey("chat_threads.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("meta", JSONB, nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "message_citations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("chat_messages.id"), nullable=False),
        sa.Column("chunk_id", UUID(as_uuid=True), sa.ForeignKey("document_chunks.id"), nullable=False),
        sa.Column("excerpt", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index("idx_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("idx_chat_threads_owner_id", "chat_threads", ["owner_id"])
    op.create_index("idx_chat_messages_thread_id", "chat_messages", ["thread_id"])
    op.create_index("idx_message_citations_message_id", "message_citations", ["message_id"])
    op.create_index("idx_message_citations_chunk_id", "message_citations", ["chunk_id"])
    op.create_index("idx_document_chunks_embedding", "document_chunks", ["embedding"], postgresql_using="hnsw", postgresql_with={"m": 16, "ef_construction": 200}, postgresql_ops={"embedding": "vector_cosine_ops"})
    op.execute("CREATE INDEX idx_document_chunks_search ON document_chunks USING GIN (search_vector)")
    op.execute("CREATE INDEX idx_document_chunks_meta ON document_chunks USING GIN (meta jsonb_path_ops)")


def downgrade() -> None:
    op.drop_table("message_citations")
    op.drop_table("chat_messages")
    op.drop_table("chat_threads")
    op.drop_table("document_chunks")
    op.drop_table("source_documents")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
