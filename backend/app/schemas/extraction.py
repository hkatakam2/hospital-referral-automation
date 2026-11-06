from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

FieldName = Literal[
    "patient_name", "date_of_birth", "referring_organization",
    "requested_specialty", "referral_reason",
]


class ReferralPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(strict=True, min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*$")
    version: str = Field(strict=True, min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(strict=True, min_length=1)
    required_fields: tuple[FieldName, ...] = Field(min_length=1)

    @field_validator("required_fields")
    @classmethod
    def unique_fields(cls, fields):
        if len(set(fields)) != len(fields):
            raise ValueError("Policy requirements must be unique")
        return fields

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, name):
        if not name.strip():
            raise ValueError("Policy name must not be blank")
        return name


class PolicyRequirementResult(BaseModel):
    field: FieldName
    satisfied: bool
    finding: Literal["found", "missing", "conflicting", "invalid"]


class PolicyAssessment(BaseModel):
    policy: ReferralPolicy
    requirements: list[PolicyRequirementResult]
    source_coverage_satisfied: bool


class SourcePage(BaseModel):
    page_number: int
    text: str


class SourceDocument(BaseModel):
    document_id: UUID
    parse_status: Literal["parsed", "partial"]
    pages: list[SourcePage]


class Evidence(BaseModel):
    document_id: UUID
    page_number: int
    quote: str


class Candidate(BaseModel):
    raw_value: str
    value: str | None
    issue: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class FieldResult(BaseModel):
    value: str | None = None
    candidates: list[Candidate] = Field(default_factory=list)


class Finding(BaseModel):
    field: FieldName
    status: Literal["found", "missing", "conflicting", "invalid"]


class ExtractionProvenance(BaseModel):
    evidence_version: str
    candidates_checked: int
    candidates_rejected: int
    provider: str | None = None
    model: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    request_ms: float | None = None


class ExtractionDetail(BaseModel):
    id: UUID
    referral_id: UUID
    extractor_version: str
    checklist_version: str
    created_at: datetime
    source_document_ids: list[UUID]
    fields: dict[FieldName, FieldResult]
    findings: list[Finding]
    warnings: list[str]
    complete: bool
    provenance: ExtractionProvenance | None = None
    policy_assessment: PolicyAssessment | None = None


class ExtractionSummary(BaseModel):
    id: UUID
    referral_id: UUID
    extractor_version: str
    checklist_version: str
    created_at: datetime
    source_document_ids: list[UUID]
    complete: bool


ExtractorChoice = Literal["rules", "gemini"]


class ExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    extractor: ExtractorChoice = "rules"


class ExtractionMethod(BaseModel):
    extractor: ExtractorChoice
    available: bool
    reason: str | None = None
