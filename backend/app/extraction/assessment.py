from collections.abc import Sequence
from typing import get_args

from pydantic import BaseModel, Field

from app.extraction.base import ExecutionMetadata, ExtractionOutput, Extractor
from app.extraction.grounding import candidate_evidence_issue
from app.extraction.normalization import normalize_claim
from app.schemas.extraction import FieldName, FieldResult, Finding, SourceDocument

CHECKLIST_VERSION = "five-required-fields/2"
REQUIRED_FIELDS: tuple[FieldName, ...] = get_args(FieldName)


class ExtractionAssessment(BaseModel):
    original_output: ExtractionOutput | None = Field(default=None, exclude=True)
    evidence_checks: dict[str, int] = Field(default_factory=dict, exclude=True)
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
    checks = {"checked": 0, "rejected": 0}
    for field in REQUIRED_FIELDS:
        # The assessment owns selection and classification, not the extractor.
        # Copy candidates so an assessment never mutates an adapter's output.
        result = extracted.get(field, FieldResult()).model_copy(deep=True)
        result.value = None
        for candidate in result.candidates:
            checks["checked"] += 1
            issue = candidate_evidence_issue(candidate.raw_value, candidate.evidence, sources)
            if issue is None and candidate.value is not None:
                expected, normalization_issue = normalize_claim(
                    field, candidate.raw_value, candidate.value,
                )
                if normalization_issue or candidate.value != expected:
                    issue = normalization_issue or (
                        "Selected value does not match source normalization"
                    )
            if issue:
                checks["rejected"] += 1
                candidate.value = None
                candidate.issue = issue
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
        original_output=output.model_copy(deep=True), evidence_checks=checks,
        execution=output.execution, extractor_version=extractor.version,
        checklist_version=CHECKLIST_VERSION,
        fields=fields, findings=findings, warnings=warnings,
        complete=bool(sources) and not warnings and all(f.status == "found" for f in findings),
    )
