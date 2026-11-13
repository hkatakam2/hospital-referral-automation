from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReferralRecord(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        CheckConstraint("status IN ('received', 'missing_information', 'review_required')",
                        name="workflow_status"),
        CheckConstraint("workflow_version >= 0", name="workflow_version_nonnegative"),
        CheckConstraint("values_version >= 0", name="values_version_nonnegative"),
        CheckConstraint("btrim(patient_name) <> ''", name="patient_name_not_blank"),
        CheckConstraint("btrim(referring_organization) <> ''", name="organization_not_blank"),
        CheckConstraint("btrim(referral_reason) <> ''", name="reason_not_blank"),
        CheckConstraint("requested_specialty = 'cardiology'", name="cardiology_only"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    patient_name: Mapped[str] = mapped_column(Text)
    date_of_birth: Mapped[date] = mapped_column(Date)
    referring_organization: Mapped[str] = mapped_column(Text)
    requested_specialty: Mapped[str] = mapped_column(Text)
    referral_reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default="received")
    workflow_version: Mapped[int] = mapped_column(Integer, server_default="0")
    values_version: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
