from datetime import date, datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ReferralCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_name: RequiredText
    date_of_birth: date
    referring_organization: RequiredText
    requested_specialty: Literal["cardiology"]
    referral_reason: RequiredText

    @field_validator("date_of_birth")
    @classmethod
    def reject_future_date_of_birth(cls, value: date) -> date:
        if value > datetime.now(timezone.utc).date():
            raise ValueError("Date of birth must not be in the future")
        return value


class Referral(ReferralCreate):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    created_at: datetime
