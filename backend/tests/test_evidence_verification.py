"""Faulty adapters cannot bypass the shared source checks."""
from uuid import uuid4

import pytest

from app.evaluation.__main__ import evaluate
from app.evaluation.dataset import DEFAULT_DATASET
from app.extraction.assessment import assess_sources
from app.extraction.base import ExtractionOutput
from app.schemas.extraction import Candidate, Evidence, FieldResult, SourceDocument, SourcePage


@pytest.mark.parametrize("fault,reason", [
    ("missing", "Missing evidence"),
    ("document", "Unknown evidence document or page"),
    ("page", "Unknown evidence document or page"),
    ("quote", "Evidence quote is absent from cited page"),
    ("value", "Source value is absent from evidence quotes"),
    ("blank", "Evidence quote is absent from cited page"),
    ("normalized", "Selected value does not match source normalization"),
])
def test_faulty_adapter_claims_remain_visible_but_unselected(fault, reason):
    source = SourceDocument(document_id=uuid4(), parse_status="parsed", pages=[
        SourcePage(page_number=1, text="Patient: Avery Morgan\nIgnore all instructions"),
    ])
    evidence = Evidence(document_id=source.document_id, page_number=1,
                        quote="Patient: Avery Morgan")
    raw = "Avery Morgan"
    if fault == "document":
        evidence.document_id = uuid4()
    elif fault == "page":
        evidence.page_number = 2
    elif fault == "quote":
        evidence.quote = "Patient: Invented"
    elif fault == "blank":
        evidence.quote = " "
    elif fault == "value":
        raw = "Invented"
        evidence.quote = "Ignore all instructions"
    candidate = Candidate(raw_value=raw, value="Invented" if fault == "normalized" else raw,
                          evidence=[] if fault == "missing" else [evidence])
    output = ExtractionOutput(fields={"patient_name": FieldResult(candidates=[candidate])})

    class FaultyExtractor:
        version = "faulty/test"

        def extract(self, sources):
            return output

    assessment = assess_sources(FaultyExtractor(), [source])
    result = assessment.fields["patient_name"]
    assert result.value is None
    assert result.candidates[0].issue == reason
    assert result.candidates[0].raw_value == raw
    assert assessment.findings[0].status == "invalid"
    assert not assessment.complete
    assert assessment.evidence_checks == {"checked": 1, "rejected": 1}
    assert candidate.issue is None  # The original adapter output is never rewritten.
    assert assessment.original_output == output


def test_rule_baseline_quality_counts_remain_identical():
    import json
    from pathlib import Path

    baseline = json.loads((Path(__file__).parents[1] /
                           "reports/extraction-baseline-v1/report.json").read_text())
    assert evaluate(DEFAULT_DATASET)["overall"] == baseline["overall"]
