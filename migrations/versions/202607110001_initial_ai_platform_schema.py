"""Initial AI platform schema.

Revision ID: 202607110001
Revises:
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607110001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Timestamp when the record was created.",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Timestamp when the record was last updated.",
        ),
    ]


def uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        primary_key=True,
        nullable=False,
        comment="Unique identifier for the record.",
    )


def metadata_column() -> sa.Column:
    return sa.Column(
        "metadata",
        postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
        comment="Additional structured metadata for the record.",
    )


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        uuid_pk(),
        sa.Column("email", sa.String(length=320), nullable=False, comment="User email address."),
        sa.Column(
            "full_name", sa.String(length=255), nullable=True, comment="User display name."
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="Whether the user account is active.",
        ),
        *timestamps(),
        sa.UniqueConstraint("email", name="uq_users_email"),
        comment="Application users who own conversations, documents, and integrations.",
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "documents",
        uuid_pk(),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Identifier of the user who owns the document.",
        ),
        sa.Column("source", sa.String(length=50), nullable=False, comment="Document source type."),
        sa.Column(
            "external_id",
            sa.String(length=255),
            nullable=True,
            comment="Document identifier in the source system.",
        ),
        sa.Column("title", sa.String(length=500), nullable=False, comment="Document title."),
        sa.Column(
            "mime_type", sa.String(length=255), nullable=True, comment="Document MIME type."
        ),
        sa.Column("url", sa.Text(), nullable=True, comment="Original document URL."),
        sa.Column(
            "checksum", sa.String(length=128), nullable=True, comment="Document content checksum."
        ),
        metadata_column(),
        sa.Column(
            "indexed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when the document was indexed.",
        ),
        *timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        comment="Documents indexed for retrieval and AI-assisted search.",
    )
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_index("ix_documents_source", "documents", ["source"])
    op.create_index("ix_documents_external_id", "documents", ["external_id"])
    op.create_index("ix_documents_checksum", "documents", ["checksum"])

    op.create_table(
        "document_chunks",
        uuid_pk(),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Identifier of the parent document.",
        ),
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=False,
            comment="Chunk position in the document.",
        ),
        sa.Column("content", sa.Text(), nullable=False, comment="Text content of the chunk."),
        sa.Column(
            "token_count",
            sa.Integer(),
            nullable=True,
            comment="Estimated token count of the chunk.",
        ),
        sa.Column(
            "embedding_id",
            sa.String(length=255),
            nullable=True,
            comment="Identifier of the vector-store embedding.",
        ),
        sa.Column(
            "embedding_model",
            sa.String(length=120),
            nullable=True,
            comment="Model used to generate the embedding.",
        ),
        metadata_column(),
        *timestamps(),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_position"),
        comment="Searchable text chunks derived from indexed documents.",
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_embedding_id", "document_chunks", ["embedding_id"])

    op.create_table(
        "conversations",
        uuid_pk(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Identifier of the user who owns the conversation.",
        ),
        sa.Column("title", sa.String(length=255), nullable=True, comment="Conversation title."),
        metadata_column(),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        comment="User conversations handled by AI agents.",
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        uuid_pk(),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Identifier of the parent conversation.",
        ),
        sa.Column("role", sa.String(length=40), nullable=False, comment="Message author role."),
        sa.Column("content", sa.Text(), nullable=False, comment="Message text content."),
        sa.Column(
            "tool_calls",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="Tool calls requested or produced by the message.",
        ),
        sa.Column(
            "token_count",
            sa.Integer(),
            nullable=True,
            comment="Token count of the message.",
        ),
        *timestamps(),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        comment="Messages exchanged within AI conversations.",
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_role", "messages", ["role"])

    op.create_table(
        "agent_runs",
        uuid_pk(),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Identifier of the related conversation.",
        ),
        sa.Column(
            "agent_type",
            sa.String(length=80),
            nullable=False,
            comment="Type of agent executed.",
        ),
        sa.Column(
            "status",
            sa.String(length=40),
            server_default="pending",
            nullable=False,
            comment="Current execution status of the agent run.",
        ),
        sa.Column("goal", sa.Text(), nullable=True, comment="Goal assigned to the agent."),
        sa.Column(
            "input",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="Structured input supplied to the agent.",
        ),
        sa.Column(
            "output",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="Structured output produced by the agent.",
        ),
        sa.Column(
            "trace",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="Ordered execution trace for the agent run.",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when execution started.",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when execution completed.",
        ),
        *timestamps(),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        comment="Execution records for conversation and workflow agents.",
    )
    op.create_index("ix_agent_runs_conversation_id", "agent_runs", ["conversation_id"])
    op.create_index("ix_agent_runs_agent_type", "agent_runs", ["agent_type"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    op.create_table(
        "tool_executions",
        uuid_pk(),
        sa.Column(
            "agent_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Identifier of the parent agent run.",
        ),
        sa.Column(
            "tool_name",
            sa.String(length=120),
            nullable=False,
            comment="Registered tool name.",
        ),
        sa.Column(
            "arguments",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="Arguments passed to the tool.",
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="Structured result returned by the tool.",
        ),
        sa.Column(
            "status",
            sa.String(length=40),
            server_default="pending",
            nullable=False,
            comment="Current execution status of the tool call.",
        ),
        sa.Column("error", sa.Text(), nullable=True, comment="Error message when execution fails."),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when tool execution started.",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when tool execution completed.",
        ),
        *timestamps(),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        comment="Individual tool calls executed during an agent run.",
    )
    op.create_index("ix_tool_executions_agent_run_id", "tool_executions", ["agent_run_id"])
    op.create_index("ix_tool_executions_tool_name", "tool_executions", ["tool_name"])
    op.create_index("ix_tool_executions_status", "tool_executions", ["status"])

    op.create_table(
        "sheet_sync_jobs",
        uuid_pk(),
        sa.Column(
            "spreadsheet_id",
            sa.String(length=255),
            nullable=False,
            comment="Google Sheets spreadsheet identifier.",
        ),
        sa.Column(
            "range_name", sa.String(length=255), nullable=False, comment="Target A1 notation range."
        ),
        sa.Column(
            "operation",
            sa.String(length=40),
            nullable=False,
            comment="Sheets operation type.",
        ),
        sa.Column(
            "status",
            sa.String(length=40),
            server_default="pending",
            nullable=False,
            comment="Current status of the synchronization job.",
        ),
        sa.Column(
            "rows_processed",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Number of rows processed by the operation.",
        ),
        metadata_column(),
        *timestamps(),
        comment="Audit records for Google Sheets read and append operations.",
    )
    op.create_index("ix_sheet_sync_jobs_spreadsheet_id", "sheet_sync_jobs", ["spreadsheet_id"])
    op.create_index("ix_sheet_sync_jobs_operation", "sheet_sync_jobs", ["operation"])
    op.create_index("ix_sheet_sync_jobs_status", "sheet_sync_jobs", ["status"])

    op.create_table(
        "scraped_pages",
        uuid_pk(),
        sa.Column("url", sa.Text(), nullable=False, comment="Final URL of the scraped page."),
        sa.Column("title", sa.String(length=500), nullable=True, comment="Extracted page title."),
        sa.Column(
            "text_content",
            sa.Text(),
            nullable=False,
            comment="Extracted readable page text.",
        ),
        sa.Column(
            "status_code",
            sa.Integer(),
            nullable=False,
            comment="HTTP response status code.",
        ),
        sa.Column(
            "content_hash",
            sa.String(length=128),
            nullable=False,
            comment="SHA-256 hash of the extracted text.",
        ),
        metadata_column(),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Timestamp when the page was scraped.",
        ),
        *timestamps(),
        comment="Web pages fetched and converted to readable text.",
    )
    op.create_index("ix_scraped_pages_url", "scraped_pages", ["url"])
    op.create_index("ix_scraped_pages_content_hash", "scraped_pages", ["content_hash"])

    op.create_table(
        "voice_sessions",
        uuid_pk(),
        sa.Column(
            "provider",
            sa.String(length=80),
            nullable=False,
            comment="Voice service provider.",
        ),
        sa.Column(
            "call_sid", sa.String(length=120), nullable=True, comment="Provider-specific call ID."
        ),
        sa.Column(
            "phone_from", sa.String(length=80), nullable=True, comment="Caller phone number."
        ),
        sa.Column(
            "phone_to", sa.String(length=80), nullable=True, comment="Recipient phone number."
        ),
        sa.Column("transcript", sa.Text(), nullable=True, comment="Text transcript of the call."),
        sa.Column(
            "audio_url",
            sa.Text(),
            nullable=True,
            comment="URL of the recorded or generated audio.",
        ),
        sa.Column(
            "status",
            sa.String(length=40),
            server_default="started",
            nullable=False,
            comment="Current status of the voice session.",
        ),
        metadata_column(),
        *timestamps(),
        sa.UniqueConstraint("call_sid", name="uq_voice_sessions_call_sid"),
        comment="Inbound and synthesized voice interaction sessions.",
    )
    op.create_index("ix_voice_sessions_provider", "voice_sessions", ["provider"])
    op.create_index("ix_voice_sessions_call_sid", "voice_sessions", ["call_sid"])
    op.create_index("ix_voice_sessions_status", "voice_sessions", ["status"])

    op.create_table(
        "integration_credentials",
        uuid_pk(),
        sa.Column(
            "provider",
            sa.String(length=80),
            nullable=False,
            comment="External integration provider.",
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Identifier of the user who owns the credential.",
        ),
        sa.Column(
            "account_id",
            sa.String(length=255),
            nullable=True,
            comment="Account identifier at the external provider.",
        ),
        sa.Column(
            "secret_ref",
            sa.String(length=500),
            nullable=False,
            comment="Reference to the externally stored secret.",
        ),
        sa.Column(
            "scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="Authorization scopes granted to the integration.",
        ),
        metadata_column(),
        *timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        comment="References to credentials for external service integrations.",
    )
    op.create_index("ix_integration_credentials_provider", "integration_credentials", ["provider"])
    op.create_index("ix_integration_credentials_owner_id", "integration_credentials", ["owner_id"])
    op.create_index(
        "ix_integration_credentials_account_id",
        "integration_credentials",
        ["account_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_integration_credentials_account_id", table_name="integration_credentials")
    op.drop_index("ix_integration_credentials_owner_id", table_name="integration_credentials")
    op.drop_index("ix_integration_credentials_provider", table_name="integration_credentials")
    op.drop_table("integration_credentials")

    op.drop_index("ix_voice_sessions_status", table_name="voice_sessions")
    op.drop_index("ix_voice_sessions_call_sid", table_name="voice_sessions")
    op.drop_index("ix_voice_sessions_provider", table_name="voice_sessions")
    op.drop_table("voice_sessions")

    op.drop_index("ix_scraped_pages_content_hash", table_name="scraped_pages")
    op.drop_index("ix_scraped_pages_url", table_name="scraped_pages")
    op.drop_table("scraped_pages")

    op.drop_index("ix_sheet_sync_jobs_status", table_name="sheet_sync_jobs")
    op.drop_index("ix_sheet_sync_jobs_operation", table_name="sheet_sync_jobs")
    op.drop_index("ix_sheet_sync_jobs_spreadsheet_id", table_name="sheet_sync_jobs")
    op.drop_table("sheet_sync_jobs")

    op.drop_index("ix_tool_executions_status", table_name="tool_executions")
    op.drop_index("ix_tool_executions_tool_name", table_name="tool_executions")
    op.drop_index("ix_tool_executions_agent_run_id", table_name="tool_executions")
    op.drop_table("tool_executions")

    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_agent_type", table_name="agent_runs")
    op.drop_index("ix_agent_runs_conversation_id", table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_index("ix_messages_role", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")

    op.drop_index("ix_document_chunks_embedding_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_documents_checksum", table_name="documents")
    op.drop_index("ix_documents_external_id", table_name="documents")
    op.drop_index("ix_documents_source", table_name="documents")
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
