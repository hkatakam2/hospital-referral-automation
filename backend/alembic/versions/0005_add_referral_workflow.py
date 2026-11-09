"""Persist referral workflow status and coordinator action history."""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("referrals", sa.Column("status", sa.Text(), nullable=False,
                                       server_default="received"))
    op.add_column("referrals", sa.Column("workflow_version", sa.Integer(), nullable=False,
                                       server_default="0"))
    op.create_check_constraint("workflow_status", "referrals",
                               "status IN ('received', 'missing_information', 'review_required')")
    op.create_check_constraint("workflow_version_nonnegative", "referrals", "workflow_version >= 0")
    # Use the same explicit table definition as the model, without creating other tables.
    op.create_table(
        "review_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("referral_id", sa.Uuid(), sa.ForeignKey("referrals.id"), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("previous_status", sa.Text(), nullable=False),
        sa.Column("new_status", sa.Text(), nullable=False),
        sa.Column("workflow_version", sa.Integer(), nullable=False),
        sa.Column("reviewer", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_information", sa.Text()),
        sa.Column("extraction_id", sa.Uuid(), sa.ForeignKey("extraction_runs.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("referral_id", "workflow_version", name="review_event_version_unique"),
        sa.CheckConstraint("workflow_version > 0", name="review_event_version_positive"),
        sa.CheckConstraint("btrim(reviewer) <> '' AND btrim(reason) <> ''",
                           name="review_event_text"),
        sa.CheckConstraint(
            "(action = 'request_missing_information' "
            "AND previous_status IN ('received', 'review_required') "
            "AND new_status = 'missing_information' "
            "AND requested_information IS NOT NULL AND btrim(requested_information) <> '') OR "
            "(action = 'resume_review' AND previous_status = 'missing_information' "
            "AND new_status = 'review_required' AND requested_information IS NULL "
            "AND extraction_id IS NULL)", name="review_event_transition",
        ),
    )
    op.create_index("ix_review_events_referral_id", "review_events", ["referral_id"])


def downgrade():
    op.drop_table("review_events")
    op.drop_constraint("workflow_status", "referrals", type_="check")
    op.drop_constraint("workflow_version_nonnegative", "referrals", type_="check")
    op.drop_column("referrals", "workflow_version")
    op.drop_column("referrals", "status")
