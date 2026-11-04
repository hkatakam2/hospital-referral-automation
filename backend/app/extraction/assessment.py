from collections.abc import Sequence
from typing import get_args

from pydantic import BaseModel, Field

from app.extraction.base import ExecutionMetadata, Extractor
from app.schemas.extraction import FieldName, FieldResult, Finding, SourceDocument

CHECKLIST_VERSION = "five-required-fields/2"
REQUIRED_FIELDS: tuple[FieldName, ...] = get_args(FieldName)


class ExtractionAssessment(BaseModel):
    execution: ExecutionMetadata = Field(default_factory=ExecutionMetadata, exclude=True)
    extractor_version: str
    checklist_version: str
    fields: dict[FieldName, FieldResult]
    findings: list[Finding]
    warnings: list[str]
    complete: bool


def assess_sources(extractor: Extractor, sources: Sequence[SourceDocument]) -> ExtractionAssessment:
    """Assess candidates and source coverage together, without persistence or approval."""
    output = extractor.extract(sources)
    extracted = output.fields
    if set(extracted) - set(REQUIRED_FIELDS):
        raise ValueError("Extractor returned unknown referral fields")
    fields = {}
    findings = []
    for field in REQUIRED_FIELDS:
        # The assessment owns selection and classification, not the extractor.
        # Copy candidates so an assessment never mutates an adapter's output.
        result = extracted.get(field, FieldResult()).model_copy(deep=True)
        result.value = None
        for candidate in result.candidates:
            if candidate.value is None and candidate.issue is None:
                candidate.issue = "No normalized value"
        if not result.candidates:
            status = "missing"
        elif any(candidate.issue is not None for candidate in result.candidates):
            status = "invalid"
        elif len(result.candidates) > 1:
            status = "conflicting"
        else:
            status = "found"
            result.value = result.candidates[0].value
        fields[field] = result
        findings.append(Finding(field=field, status=status))
    warnings = [
        f"Document {source.document_id} has pages without usable text; "
        "source coverage is incomplete"
        for source in sources if source.parse_status == "partial"
    ]
    return ExtractionAssessment(
        execution=output.execution, extractor_version=extractor.version,
        checklist_version=CHECKLIST_VERSION,
        fields=fields, findings=findings, warnings=warnings,
        complete=bool(sources) and not warnings and all(f.status == "found" for f in findings),
    )
