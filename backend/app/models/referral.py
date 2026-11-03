from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReferralRecord(Base):
    __tablename__ = "referrals"
    __table_args__ = (
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
