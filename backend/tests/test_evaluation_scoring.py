import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.evaluation.__main__ import evaluate, markdown
from app.evaluation.dataset import DEFAULT_DATASET, load_dataset
from app.evaluation.scoring import score_packet, summarize
from app.extraction.assessment import ExtractionAssessment
from app.extraction.base import ExtractionOutput
from app.schemas.extraction import Candidate, FieldResult, Finding


def packet_named(name="standard-labels"):
    return next(packet for packet in load_dataset().packets if packet.id == name)


def perfect_assessment(packet):
    # A hand-built prediction isolates scorer behavior from production extraction.
    return ExtractionAssessment(
        extractor_version="test", checklist_version="test", warnings=[], complete=packet.complete,
        fields={name: FieldResult(value=annotation.value, candidates=[Candidate(
            raw_value=annotation.value or "conflicting/invalid", value=annotation.value,
            evidence=annotation.evidence,
        )] if annotation.evidence else []) for name, annotation in packet.expected.items()},
        findings=[Finding(field=name, status=annotation.status)
                  for name, annotation in packet.expected.items()],
    )


def test_wrong_selection_counts_as_false_positive_and_false_negative():
    packet = packet_named()
    actual = perfect_assessment(packet)
    actual.fields["patient_name"].value = "Someone Else"
    summary = summarize([score_packet(packet, actual)])
    assert summary["counts"]["value_tp"] == 4
    assert summary["counts"]["value_fp"] == 1
    assert summary["counts"]["value_fn"] == 1
    assert summary["metrics"]["value_precision"]["rate"] == .8
    assert summary["metrics"]["value_recall"]["rate"] == .8
    assert summary["metrics"]["exact_match_accuracy"]["rate"] == .8


def test_abstention_on_present_value_reduces_recall_and_adds_false_missing():
    packet = packet_named()
    actual = perfect_assessment(packet)
    actual.fields["date_of_birth"] = FieldResult()
    actual.findings[1].status = "missing"
    summary = summarize([score_packet(packet, actual)])
    assert summary["counts"]["value_fp"] == 0
    assert summary["counts"]["value_fn"] == 1
    assert summary["counts"]["missing_fp"] == 1
    assert summary["metrics"]["value_precision"]["rate"] == 1
    assert summary["metrics"]["value_recall"]["rate"] == .8


def test_hallucinated_value_on_missing_field_counts_false_completeness():
    packet = packet_named("missing-referring_organization")
    actual = perfect_assessment(packet)
    actual.fields["referring_organization"].value = "Invented Clinic"
    actual.findings[2].status = "found"
    actual.complete = True
    metrics = summarize([score_packet(packet, actual)])["metrics"]
    assert metrics["missing_recall"] == {"numerator": 0, "denominator": 1, "rate": 0}
    assert metrics["false_completeness_rate"] == {
        "numerator": 1, "denominator": 1, "rate": 1,
    }
    assert metrics["value_precision"]["rate"] == .8


@pytest.mark.parametrize("name,status", [
    ("conflicting-date_of_birth", "conflicting"), ("impossible-dob", "invalid"),
])
def test_null_exact_match_does_not_hide_wrong_finding(name, status):
    packet = packet_named(name)
    actual = perfect_assessment(packet)
    actual.findings[1].status = "missing"
    metrics = summarize([score_packet(packet, actual)])["metrics"]
    assert metrics["exact_match_accuracy"]["rate"] == 1
    assert metrics["finding_accuracy"]["rate"] == .8
    assert metrics[f"{status}_recall"]["rate"] == 0


def test_partial_coverage_is_in_false_completeness_denominator():
    packet = packet_named("blank-second-page")
    actual = perfect_assessment(packet)
    actual.complete = True
    assert summarize([score_packet(packet, actual)])["metrics"][
        "false_completeness_rate"
    ]["rate"] == 1


def test_evidence_checks_document_page_and_exact_quote_with_counts():
    packet = packet_named()
    actual = perfect_assessment(packet).model_copy(deep=True)
    actual.fields["patient_name"].candidates[0].evidence[0].page_number = 2
    row = score_packet(packet, actual)
    metrics = summarize([row])["metrics"]
    assert metrics["evidence_precision"]["rate"] == .8
    assert metrics["evidence_recall"]["rate"] == .8
    assert len(row["failures"][0]["missing_evidence"]) == 1
    assert len(row["failures"][0]["unexpected_evidence"]) == 1


def test_duplicate_evidence_is_scored_as_a_set():
    packet = packet_named()
    actual = perfect_assessment(packet).model_copy(deep=True)
    candidate = actual.fields["patient_name"].candidates[0]
    candidate.evidence.append(candidate.evidence[0])
    assert not score_packet(packet, actual)["failures"]


def test_zero_denominators_are_undefined_not_perfect_scores():
    packet = packet_named()
    metrics = summarize([score_packet(packet, perfect_assessment(packet))])["metrics"]
    assert metrics["missing_precision"]["rate"] is None
    assert metrics["missing_recall"]["rate"] is None
    assert metrics["false_completeness_rate"]["rate"] is None


def test_report_is_reproducible_except_timing_and_contains_failure_examples():
    first = evaluate(DEFAULT_DATASET)
    second = evaluate(DEFAULT_DATASET)
    assert first.pop("latency_ms")["samples"] == 30
    second.pop("latency_ms")
    assert first == second
    assert first["overall"]["counts"]["fields"] == 150
    assert sum(group["counts"]["fields"] for group in first["by_document_type"].values()) == 150
    failures = {row["packet_id"] for row in first["packets"] if row["failures"]}
    assert "narrative-letter" in failures
    assert "standard-labels" not in failures


def test_cli_writes_parseable_json_and_markdown_without_database(tmp_path):
    process = subprocess.run(
        [sys.executable, "-m", "app.evaluation", "--output", str(tmp_path)],
        cwd=Path(__file__).parents[1], capture_output=True, text=True, check=True,
    )
    report = json.loads((tmp_path / "report.json").read_text())
    assert "Evaluated 30 packets" in process.stdout
    assert report["packet_count"] == 30
    rendered = (tmp_path / "report.md").read_text()
    assert rendered == markdown(report)
    assert "narrative-letter" in rendered
    assert "150" in rendered


def test_evaluator_accepts_another_adapter_and_does_not_drop_failed_packets():
    class AbstainingExtractor:
        version = "abstain/test"

        def extract(self, sources):
            return ExtractionOutput(fields={})

    report = evaluate(DEFAULT_DATASET, AbstainingExtractor())
    assert report["extractor_version"] == "abstain/test"
    assert report["packet_count"] == 30
    assert report["overall"]["metrics"]["value_recall"]["rate"] == 0
    assert report["overall"]["metrics"]["value_precision"]["rate"] is None

    class BrokenExtractor:
        version = "broken/test"

        def extract(self, sources):
            raise RuntimeError("Extraction failed")

    with pytest.raises(RuntimeError, match="Extraction failed"):
        evaluate(DEFAULT_DATASET, BrokenExtractor())


def test_cli_rejects_invalid_dataset_without_publishing_report(tmp_path):
    dataset = tmp_path / "bad.json"
    dataset.write_text('{"version": "bad", "description": "empty", "packets": []}')
    output = tmp_path / "output"
    process = subprocess.run(
        [sys.executable, "-m", "app.evaluation", "--dataset", str(dataset),
         "--output", str(output)],
        cwd=Path(__file__).parents[1], capture_output=True, text=True,
    )
    assert process.returncode != 0
    assert not output.exists()
