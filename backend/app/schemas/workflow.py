from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

WorkflowStatus = Literal["received", "missing_information", "review_required"]
WorkflowAction = Literal["request_missing_information", "resume_review"]
ReviewText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class WorkflowCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer: ReviewText
    reason: ReviewText
    expected_workflow_version: int = Field(ge=0, strict=True)


class InformationRequest(WorkflowCommand):
    requested_information: ReviewText
    extraction_id: UUID | None = None


class ReviewEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    referral_id: UUID
    action: WorkflowAction
    previous_status: WorkflowStatus
    new_status: WorkflowStatus
    workflow_version: int
    reviewer: str
    reason: str
    requested_information: str | None
    extraction_id: UUID | None
    created_at: datetime
