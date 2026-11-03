"""Create durable manual referral storage.

Revision ID: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "referrals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_name", sa.Text(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("referring_organization", sa.Text(), nullable=False),
        sa.Column("requested_specialty", sa.Text(), nullable=False),
        sa.Column("referral_reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("btrim(patient_name) <> ''", name="patient_name_not_blank"),
        sa.CheckConstraint("btrim(referring_organization) <> ''", name="organization_not_blank"),
        sa.CheckConstraint("btrim(referral_reason) <> ''", name="reason_not_blank"),
        sa.CheckConstraint("requested_specialty = 'cardiology'", name="cardiology_only"),
    )


def downgrade():
    op.drop_table("referrals")
