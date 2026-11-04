"""Model claims are separate from application-selected values and findings."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ClaimedEvidence(StrictClaim):
    document_id: UUID
    page_number: int = Field(ge=1)
    quote: str = Field(min_length=1)


class ClaimedCandidate(StrictClaim):
    source_value: str = Field(min_length=1)
    proposed_value: str | None
    evidence: list[ClaimedEvidence] = Field(min_length=1)


class LLMClaims(StrictClaim):
    patient_name: list[ClaimedCandidate]
    date_of_birth: list[ClaimedCandidate]
    referring_organization: list[ClaimedCandidate]
    requested_specialty: list[ClaimedCandidate]
    referral_reason: list[ClaimedCandidate]
