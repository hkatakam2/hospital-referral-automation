from app.schemas.extraction import FieldName, FieldResult, Finding, SourceDocument

CHECKLIST_VERSION = "five-required-fields/1"


def check_completeness(
    fields: dict[FieldName, FieldResult], sources: list[SourceDocument],
) -> tuple[list[Finding], list[str], bool]:
    findings = []
    for field, result in fields.items():
        if not result.candidates:
            status = "missing"
        elif any(c.issue is not None for c in result.candidates):
            status = "invalid"
        elif len(result.candidates) > 1:
            status = "conflicting"
        else:
            status = "found"
        findings.append(Finding(field=field, status=status))
    warnings = [
        f"Document {source.document_id} has pages without usable text; "
        "source coverage is incomplete"
        for source in sources if source.parse_status == "partial"
    ]
    complete = not warnings and all(f.status == "found" for f in findings)
    return findings, warnings, complete
