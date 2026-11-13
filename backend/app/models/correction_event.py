from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CorrectionEventRecord(Base):
    __tablename__ = "correction_events"
    __table_args__ = (
        UniqueConstraint("referral_id", "values_version",
                         name="correction_event_version_unique"),
        CheckConstraint("values_version > 0", name="correction_event_version_positive"),
        CheckConstraint("btrim(reviewer) <> '' AND btrim(reason) <> ''",
                        name="correction_event_text"),
        CheckConstraint("jsonb_typeof(changes) = 'object' AND changes <> '{}'::jsonb",
                        name="correction_event_changes"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    referral_id: Mapped[UUID] = mapped_column(ForeignKey("referrals.id"), index=True)
    values_version: Mapped[int] = mapped_column(Integer)
    reviewer: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    changes: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
