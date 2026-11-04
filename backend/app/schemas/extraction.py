from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

FieldName = Literal[
    "patient_name", "date_of_birth", "referring_organization",
    "requested_specialty", "referral_reason",
]


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


class ExtractionSummary(BaseModel):
    id: UUID
    referral_id: UUID
    extractor_version: str
    checklist_version: str
    created_at: datetime
    source_document_ids: list[UUID]
    complete: bool
