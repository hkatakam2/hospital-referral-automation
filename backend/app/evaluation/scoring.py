"""Explicit counts before rates; wrong selections count as both FP and FN."""

from collections import Counter
from typing import Any

from app.evaluation.dataset import Packet
from app.extraction.assessment import EXTRACTION_FIELDS, ExtractionAssessment


def evidence_keys(evidence):
    return {(str(item.document_id), item.page_number, item.quote) for item in evidence}


def score_packet(packet: Packet, actual: ExtractionAssessment) -> dict[str, Any]:
    statuses = {finding.field: finding.status for finding in actual.findings}
    fields = {}
    failures = []
    for name in EXTRACTION_FIELDS:
        expected = packet.expected[name]
        result = actual.fields[name]
        selected = result.value is not None
        available = expected.value is not None
        correct = available and result.value == expected.value
        observed_evidence = evidence_keys([
            evidence for candidate in result.candidates for evidence in candidate.evidence
        ])
        expected_evidence = evidence_keys(expected.evidence)
        counts = Counter({
            "fields": 1,
            "value_tp": int(correct),
            "value_fp": int(selected and not correct),
            "value_fn": int(available and not correct),
            "exact_matches": int(result.value == expected.value),
            "status_matches": int(statuses[name] == expected.status),
            "evidence_tp": len(observed_evidence & expected_evidence),
            "evidence_fp": len(observed_evidence - expected_evidence),
            "evidence_fn": len(expected_evidence - observed_evidence),
        })
        for status in ("missing", "conflicting", "invalid"):
            predicted = statuses[name] == status
            target = expected.status == status
            counts[f"{status}_tp"] = int(predicted and target)
            counts[f"{status}_fp"] = int(predicted and not target)
            counts[f"{status}_fn"] = int(target and not predicted)
        fields[name] = dict(counts)
        if (result.value != expected.value or statuses[name] != expected.status
                or observed_evidence != expected_evidence):
            failures.append({
                "field": name,
                "expected_value": expected.value, "actual_value": result.value,
                "expected_status": expected.status, "actual_status": statuses[name],
                "missing_evidence": sorted(expected_evidence - observed_evidence),
                "unexpected_evidence": sorted(observed_evidence - expected_evidence),
            })
    return {
        "packet_id": packet.id, "document_type": packet.document_type,
        "expected_complete": packet.complete, "actual_complete": actual.complete,
        "fields": fields, "failures": failures,
    }


def fraction(numerator: int, denominator: int) -> dict:
    return {"numerator": numerator, "denominator": denominator,
            "rate": numerator / denominator if denominator else None}


def summarize(rows: list[dict], field: str | None = None) -> dict:
    counts = Counter()
    for row in rows:
        for name, item in row["fields"].items():
            if field is None or name == field:
                counts.update(item)
    metrics = {
        "exact_match_accuracy": fraction(counts["exact_matches"], counts["fields"]),
        "finding_accuracy": fraction(counts["status_matches"], counts["fields"]),
    }
    for metric in ("value", "evidence", "missing", "conflicting", "invalid"):
        tp, fp, fn = (counts[f"{metric}_{suffix}"] for suffix in ("tp", "fp", "fn"))
        metrics[f"{metric}_precision"] = fraction(tp, tp + fp)
        metrics[f"{metric}_recall"] = fraction(tp, tp + fn)
    if field is None:
        incomplete = sum(not row["expected_complete"] for row in rows)
        false_complete = sum(
            row["actual_complete"] and not row["expected_complete"] for row in rows
        )
        metrics["false_completeness_rate"] = fraction(false_complete, incomplete)
        metrics["packet_completeness_accuracy"] = fraction(sum(
            row["actual_complete"] == row["expected_complete"] for row in rows
        ), len(rows))
    return {"counts": dict(sorted(counts.items())), "metrics": metrics}
