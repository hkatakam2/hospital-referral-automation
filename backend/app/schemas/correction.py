from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

FieldName = Literal["patient_name", "date_of_birth", "referring_organization",
                    "requested_specialty", "referral_reason"]


class FieldChange(BaseModel):
    previous: str
    new: str


class CorrectionEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    referral_id: UUID
    values_version: int
    reviewer: str
    reason: str
    changes: dict[FieldName, FieldChange]
    created_at: datetime
