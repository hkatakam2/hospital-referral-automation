"""Retain human corrections and version saved referral values."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("referrals", sa.Column("values_version", sa.Integer(), nullable=False,
                                       server_default="0"))
    op.create_check_constraint("values_version_nonnegative", "referrals", "values_version >= 0")
    op.create_table(
        "correction_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("referral_id", sa.Uuid(), sa.ForeignKey("referrals.id"), nullable=False),
        sa.Column("values_version", sa.Integer(), nullable=False),
        sa.Column("reviewer", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("changes", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("referral_id", "values_version",
                            name="correction_event_version_unique"),
        sa.CheckConstraint("values_version > 0", name="correction_event_version_positive"),
        sa.CheckConstraint("btrim(reviewer) <> '' AND btrim(reason) <> ''",
                           name="correction_event_text"),
        sa.CheckConstraint("jsonb_typeof(changes) = 'object' AND changes <> '{}'::jsonb",
                           name="correction_event_changes"),
    )
    op.create_index("ix_correction_events_referral_id", "correction_events", ["referral_id"])


def downgrade():
    op.drop_table("correction_events")
    op.drop_constraint("values_version_nonnegative", "referrals", type_="check")
    op.drop_column("referrals", "values_version")
