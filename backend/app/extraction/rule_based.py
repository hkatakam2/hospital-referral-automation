import re
from collections.abc import Sequence
from datetime import date, datetime, timezone

from app.schemas.extraction import Candidate, Evidence, FieldName, FieldResult, SourceDocument

LABELS: dict[FieldName, str] = {
    "patient_name": r"Patient|Patient Name",
    "date_of_birth": r"DOB|Date of Birth",
    "referring_organization": r"Referring Organization|Referring Clinic",
    "requested_specialty": r"Requested Specialty|Specialty|Requested Service",
    "referral_reason": r"Reason|Referral Reason",
}


def normalize(field: FieldName, raw: str) -> tuple[str | None, str | None]:
    value = " ".join(raw.split())
    if not value:
        return None, "Empty value"
    if field == "date_of_birth":
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError
            parsed = date.fromisoformat(value)
            if parsed > datetime.now(timezone.utc).date():
                raise ValueError
            return parsed.isoformat(), None
        except ValueError:
            return None, "Expected a valid, non-future ISO date"
    if field == "requested_specialty":
        if value.casefold() in {"cardiology", "cardiology consultation"}:
            return "cardiology", None
        return None, "Unsupported specialty"
    return value, None


class RuleBasedExtractor:
    version = "rules/1"

    def extract(self, sources: Sequence[SourceDocument]) -> dict[FieldName, FieldResult]:
        results = {field: FieldResult() for field in LABELS}
        for source in sources:
            for page in source.pages:
                for line in page.text.splitlines():
                    for field, labels in LABELS.items():
                        match = re.fullmatch(
                            rf"\s*(?:{labels})\s*:\s*(.*?)\s*", line, re.IGNORECASE,
                        )
                        if match is None:
                            continue
                        raw = match.group(1)
                        value, issue = normalize(field, raw)
                        candidates = results[field].candidates
                        candidate = next((c for c in candidates if (
                            c.value == value and c.issue == issue
                            and (value is not None or c.raw_value == raw)
                        )), None)
                        if candidate is None:
                            candidate = Candidate(raw_value=raw, value=value, issue=issue)
                            candidates.append(candidate)
                        candidate.evidence.append(Evidence(
                            document_id=source.document_id,
                            page_number=page.page_number, quote=line,
                        ))
        for result in results.values():
            if len(result.candidates) == 1 and result.candidates[0].issue is None:
                result.value = result.candidates[0].value
        return results
