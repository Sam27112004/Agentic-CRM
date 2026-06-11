"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-11 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'Active'"), nullable=False),
        sa.Column("account_value", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("churn_risk_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_contacts_email", "contacts", ["email"], unique=False)

    op.create_table(
        "threads",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("sender_email", sa.String(length=255), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'Open'"), nullable=False),
        sa.Column("assigned_to", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["sender_email"], ["contacts.email"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id"),
    )
    op.create_index("idx_threads_sender_email", "threads", ["sender_email"], unique=False)
    op.create_index("idx_threads_status", "threads", ["status"], unique=False)

    op.create_table(
        "emails",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=False),
        sa.Column("sender", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sentiment_score", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("urgency", sa.String(length=50), nullable=True),
        sa.Column("requires_human", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("raw_entities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'Received'"), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index("idx_emails_thread_id", "emails", ["thread_id"], unique=False)
    op.create_index("idx_emails_sender", "emails", ["sender"], unique=False)
    op.create_index("idx_emails_sentiment_score", "emails", ["sentiment_score"], unique=False)
    op.create_index("idx_emails_timestamp", "emails", ["timestamp"], unique=False)

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_processing_jobs_status", "processing_jobs", ["status"], unique=False)

    op.create_table(
        "actions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=False),
        sa.Column("agent_reasoning_log", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("action_type", sa.String(length=100), nullable=True),
        sa.Column("proposed_content", sa.Text(), nullable=True),
        sa.Column("is_approved", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "drafts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'Pending'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_drafts_email_id", "drafts", ["email_id"], unique=False)

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("source_doc", sa.String(length=255), nullable=True),
        sa.Column("chunk_text", sa.Text(), nullable=True),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "web_intelligence_cache",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("target_entity", sa.String(length=255), nullable=True),
        sa.Column("scraped_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=True),
        sa.Column("performed_by", sa.String(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("diff", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_log_entity", "audit_log", ["entity_type", "entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_audit_log_entity", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("web_intelligence_cache")
    op.drop_table("knowledge_chunks")
    op.drop_index("idx_drafts_email_id", table_name="drafts")
    op.drop_table("drafts")
    op.drop_table("actions")
    op.drop_index("idx_processing_jobs_status", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    op.drop_index("idx_emails_timestamp", table_name="emails")
    op.drop_index("idx_emails_sentiment_score", table_name="emails")
    op.drop_index("idx_emails_sender", table_name="emails")
    op.drop_index("idx_emails_thread_id", table_name="emails")
    op.drop_table("emails")
    op.drop_index("idx_threads_status", table_name="threads")
    op.drop_index("idx_threads_sender_email", table_name="threads")
    op.drop_table("threads")
    op.drop_index("ix_contacts_email", table_name="contacts")
    op.drop_table("contacts")
