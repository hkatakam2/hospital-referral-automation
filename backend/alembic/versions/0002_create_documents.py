"""Persist referral documents and page-level extracted text.

Revision ID: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("referral_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("parse_status", sa.String(16), nullable=False),
        sa.Column("parser_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["referral_id"], ["referrals.id"]),
        sa.UniqueConstraint("storage_key"),
        sa.CheckConstraint("size_bytes > 0", name="document_positive_size"),
        sa.CheckConstraint("page_count > 0", name="document_positive_pages"),
        sa.CheckConstraint("parse_status IN ('parsed', 'partial')", name="document_parse_status"),
        sa.CheckConstraint("length(sha256) = 64", name="document_checksum_length"),
    )
    op.create_index("ix_documents_referral_id", "documents", ["referral_id"])
    op.create_table(
        "document_pages",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_status", sa.String(16), nullable=False),
        sa.PrimaryKeyConstraint("document_id", "page_number"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.CheckConstraint("page_number > 0", name="document_page_positive_number"),
        sa.CheckConstraint(
            "text_status IN ('extracted', 'no_text')", name="document_page_text_status",
        ),
    )


def downgrade():
    op.drop_table("document_pages")
    op.drop_index("ix_documents_referral_id", table_name="documents")
    op.drop_table("documents")
