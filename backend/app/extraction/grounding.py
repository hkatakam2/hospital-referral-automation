"""Source-location checks, not semantic entailment or approval."""
from collections.abc import Sequence

from app.schemas.extraction import Evidence, SourceDocument

EVIDENCE_VERSION = "literal-source/1"


def candidate_evidence_issue(raw_value: str, evidence: Sequence[Evidence],
                             sources: Sequence[SourceDocument]) -> str | None:
    issue = evidence_issue(evidence, sources)
    if issue:
        return issue
    if not any(raw_value in item.quote for item in evidence):
        return "Source value is absent from evidence quotes"
    return None


def evidence_issue(evidence: Sequence[Evidence], sources: Sequence[SourceDocument]) -> str | None:
    pages = {(source.document_id, page.page_number): page.text
             for source in sources for page in source.pages}
    if not evidence:
        return "Missing evidence"
    for item in evidence:
        text = pages.get((item.document_id, item.page_number))
        if text is None:
            return "Unknown evidence document or page"
        if not item.quote.strip() or item.quote not in text:
            return "Evidence quote is absent from cited page"
    return None
