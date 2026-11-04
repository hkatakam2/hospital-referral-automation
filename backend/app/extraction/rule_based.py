import re
from collections.abc import Sequence

from app.extraction.base import ExtractionOutput
from app.extraction.candidates import add_candidate
from app.extraction.normalization import normalize
from app.schemas.extraction import Candidate, Evidence, FieldName, FieldResult, SourceDocument

LABELS: dict[FieldName, str] = {
    "patient_name": r"Patient|Patient Name",
    "date_of_birth": r"DOB|Date of Birth",
    "referring_organization": r"Referring Organization|Referring Clinic",
    "requested_specialty": r"Requested Specialty|Specialty|Requested Service",
    "referral_reason": r"Reason|Referral Reason",
}


class RuleBasedExtractor:
    version = "rules/1"

    def extract(self, sources: Sequence[SourceDocument]) -> ExtractionOutput:
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
                        add_candidate(results[field], Candidate(
                            raw_value=raw, value=value, issue=issue, evidence=[Evidence(
                                document_id=source.document_id,
                                page_number=page.page_number, quote=line,
                            )],
                        ))
        return ExtractionOutput(fields=results)
