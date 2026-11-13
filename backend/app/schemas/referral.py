from datetime import date, datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.workflow import ReviewText, WorkflowStatus

RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def reject_future_date_of_birth(value: date) -> date:
    if value > datetime.now(timezone.utc).date():
        raise ValueError("Date of birth must not be in the future")
    return value


DateOfBirth = Annotated[date, AfterValidator(reject_future_date_of_birth)]
Specialty = Literal["cardiology"]


class ReferralCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_name: RequiredText
    date_of_birth: DateOfBirth
    referring_organization: RequiredText
    requested_specialty: Specialty
    referral_reason: RequiredText


class ReferralUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Defaults permit omission; non-nullable types reject explicit null values.
    # Only model_dump(exclude_unset=True) is used when applying an update.
    patient_name: RequiredText = Field(default=None)
    date_of_birth: DateOfBirth = Field(default=None)
    referring_organization: RequiredText = Field(default=None)
    requested_specialty: Specialty = Field(default=None)
    referral_reason: RequiredText = Field(default=None)


class CorrectionCommand(ReferralUpdate):
    reviewer: ReviewText
    reason: ReviewText
    expected_values_version: int = Field(ge=0, strict=True)


class Referral(ReferralCreate):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    created_at: datetime
    status: WorkflowStatus
    workflow_version: int
    values_version: int
