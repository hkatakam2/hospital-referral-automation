from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReviewEventRecord(Base):
    __tablename__ = "review_events"
    __table_args__ = (
        UniqueConstraint("referral_id", "workflow_version", name="review_event_version_unique"),
        CheckConstraint("workflow_version > 0", name="review_event_version_positive"),
        CheckConstraint("btrim(reviewer) <> '' AND btrim(reason) <> ''", name="review_event_text"),
        CheckConstraint(
            "(action = 'request_missing_information' "
            "AND previous_status IN ('received', 'review_required') "
            "AND new_status = 'missing_information' "
            "AND requested_information IS NOT NULL AND btrim(requested_information) <> '') OR "
            "(action = 'resume_review' AND previous_status = 'missing_information' "
            "AND new_status = 'review_required' AND requested_information IS NULL "
            "AND extraction_id IS NULL)", name="review_event_transition",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    referral_id: Mapped[UUID] = mapped_column(ForeignKey("referrals.id"), index=True)
    action: Mapped[str] = mapped_column(Text)
    previous_status: Mapped[str] = mapped_column(Text)
    new_status: Mapped[str] = mapped_column(Text)
    workflow_version: Mapped[int] = mapped_column(Integer)
    reviewer: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    requested_information: Mapped[str | None] = mapped_column(Text)
    extraction_id: Mapped[UUID | None] = mapped_column(ForeignKey("extraction_runs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
