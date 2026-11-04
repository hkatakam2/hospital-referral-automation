"""Persist immutable extraction runs and their input document identities."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("referral_id", sa.Uuid(), sa.ForeignKey("referrals.id"), nullable=False),
        sa.Column("extractor_version", sa.Text(), nullable=False),
        sa.Column("checklist_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result_json", JSONB(), nullable=False),
    )
    op.create_index("ix_extraction_runs_referral_id", "extraction_runs", ["referral_id"])
    op.create_table(
        "extraction_run_documents",
        sa.Column("extraction_run_id", sa.Uuid(),
                  sa.ForeignKey("extraction_runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id"), primary_key=True),
    )


def downgrade():
    op.drop_table("extraction_run_documents")
    op.drop_index("ix_extraction_runs_referral_id", table_name="extraction_runs")
    op.drop_table("extraction_runs")
