"""Retain original extractor output separately from assessed public snapshots."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "extraction_artifacts",
        sa.Column("extraction_run_id", sa.Uuid(),
                  sa.ForeignKey("extraction_runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("artifact_json", JSONB(), nullable=False),
    )


def downgrade():
    op.drop_table("extraction_artifacts")
