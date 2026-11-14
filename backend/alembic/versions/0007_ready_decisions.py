"""Record administrative readiness decisions and explicit review reopening."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

OLD_TRANSITION = (
    "(action = 'request_missing_information' AND previous_status IN ('received', "
    "'review_required') AND new_status = 'missing_information' AND "
    "requested_information IS NOT NULL AND btrim(requested_information) <> '') OR "
    "(action = 'resume_review' AND previous_status = 'missing_information' AND "
    "new_status = 'review_required' AND requested_information IS NULL AND "
    "extraction_id IS NULL)"
)
READY_TRANSITION = (
    "(action = 'request_missing_information' AND previous_status IN ('received', "
    "'review_required') AND new_status = 'missing_information' AND "
    "requested_information IS NOT NULL AND btrim(requested_information) <> '' AND "
    "reviewed_values_version IS NULL) OR (action = 'resume_review' AND "
    "previous_status = 'missing_information' AND new_status = 'review_required' AND "
    "requested_information IS NULL AND extraction_id IS NULL AND "
    "reviewed_values_version IS NULL) OR (action = 'mark_ready' AND previous_status "
    "IN ('received', 'review_required') AND new_status = 'ready' AND "
    "requested_information IS NULL AND extraction_id IS NOT NULL AND "
    "reviewed_values_version IS NOT NULL AND reviewed_values_version >= 0) OR "
    "(action = 'reopen_review' AND previous_status = 'ready' AND new_status = "
    "'review_required' AND requested_information IS NULL AND extraction_id IS NULL "
    "AND reviewed_values_version IS NULL)"
)


def upgrade():
    op.add_column("review_events", sa.Column("reviewed_values_version", sa.Integer()))
    op.drop_constraint("review_event_transition", "review_events", type_="check")
    op.create_check_constraint("review_event_transition", "review_events", READY_TRANSITION)
    op.drop_constraint("workflow_status", "referrals", type_="check")
    op.create_check_constraint(
        "workflow_status",
        "referrals",
        "status IN ('received', 'missing_information', 'review_required', 'ready')",
    )


def downgrade():
    # Refuse lossy downgrade: decisions must not silently disappear from history.
    connection = op.get_bind()
    if connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM review_events "
            "WHERE action IN ('mark_ready', 'reopen_review'))"
        )
    ) or connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM referrals WHERE status = 'ready')")
    ):
        raise RuntimeError(
            "Cannot downgrade while ready decisions or reopened review history exist"
        )
    op.drop_constraint("review_event_transition", "review_events", type_="check")
    op.create_check_constraint("review_event_transition", "review_events", OLD_TRANSITION)
    op.drop_column("review_events", "reviewed_values_version")
    op.drop_constraint("workflow_status", "referrals", type_="check")
    op.create_check_constraint(
        "workflow_status",
        "referrals",
        "status IN ('received', 'missing_information', 'review_required')",
    )
