"""Run with python -m app.evaluation from backend/."""

import argparse
import hashlib
import json
import math
import platform
import statistics
from pathlib import Path
from time import perf_counter

from app.evaluation.dataset import DEFAULT_DATASET, load_dataset
from app.evaluation.scoring import score_packet, summarize
from app.extraction.assessment import REQUIRED_FIELDS, assess_sources
from app.extraction.base import Extractor
from app.extraction.rule_based import RuleBasedExtractor


def evaluate(dataset_path: Path, extractor: Extractor | None = None) -> dict:
    dataset = load_dataset(dataset_path)
    extractor = extractor if extractor is not None else RuleBasedExtractor()
    rows = []
    timings = []
    checklist_version = None
    for packet in dataset.packets:
        start = perf_counter()
        assessment = assess_sources(extractor, packet.sources)
        timings.append((perf_counter() - start) * 1000)
        checklist_version = assessment.checklist_version
        rows.append(score_packet(packet, assessment))
    return {
        "report_schema_version": 1,
        "dataset_version": dataset.version,
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "extractor_version": extractor.version, "checklist_version": checklist_version,
        "python_version": platform.python_version(),
        "packet_count": len(rows),
        "overall": summarize(rows),
        "by_field": {field: summarize(rows, field) for field in REQUIRED_FIELDS},
        "by_document_type": {
            kind: summarize([row for row in rows if row["document_type"] == kind])
            for kind in sorted({row["document_type"] for row in rows})
        },
        "latency_ms": {
            "scope": ("One in-process extraction plus assessment per packet; "
                      "no warmup, IO or scoring"),
            "samples": len(timings), "mean": statistics.mean(timings),
            "p50": statistics.median(timings),
            "p95": sorted(timings)[math.ceil(len(timings) * .95) - 1],
            "min": min(timings), "max": max(timings),
        },
        "packets": rows,
    }


def display(metric: dict) -> str:
    rate = metric["rate"]
    label = "N/A" if rate is None else f"{rate:.1%}"
    return f"{label} ({metric['numerator']}/{metric['denominator']})"


def markdown(report: dict) -> str:
    lines = [
        "# Extraction baseline", "",
        f"Dataset: `{report['dataset_version']}` ({report['packet_count']} packets)", "",
        f"SHA-256: `{report['dataset_sha256']}`", "",
        f"Extractor: `{report['extractor_version']}`; "
        f"checklist: `{report['checklist_version']}`; Python: `{report['python_version']}`.", "",
        "This curated source-text challenge set does not estimate clinical performance. "
        "See the evaluation README for scoring rules and limits.", "",
        "## Overall", "", "| Metric | Result (numerator/denominator) |", "| --- | --- |",
    ]
    for name, metric in report["overall"]["metrics"].items():
        lines.append(f"| {name} | {display(metric)} |")
    for title, key in (("By field", "by_field"), ("By document type", "by_document_type")):
        lines.extend(["", f"## {title}", "",
                      "| Group | Value precision | Value recall | Exact match | Finding accuracy |",
                      "| --- | --- | --- | --- | --- |"])
        for name, summary in report[key].items():
            metrics = summary["metrics"]
            cells = [display(metrics[k]) for k in (
                "value_precision", "value_recall", "exact_match_accuracy", "finding_accuracy",
            )]
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
    latency = report["latency_ms"]
    lines.extend(["", "## Processing latency", "", latency["scope"] + ".", "",
                  f"{latency['samples']} samples; mean {latency['mean']:.3f} ms; "
                  f"p50 {latency['p50']:.3f} ms; p95 {latency['p95']:.3f} ms. "
                  "Timing varies by machine and run.", "", "## Failure examples", ""])
    for row in report["packets"]:
        if not row["failures"] and row["expected_complete"] == row["actual_complete"]:
            continue
        lines.extend([f"### {row['packet_id']} ({row['document_type']})", "",
                      f"Complete: expected `{row['expected_complete']}`, "
                      f"actual `{row['actual_complete']}`.", ""])
        for failure in row["failures"]:
            # JSON quoting preserves whitespace and prevents fixture text altering Markdown.
            details = json.dumps(failure, ensure_ascii=True)
            lines.extend(["```json", details, "```", ""])
    if not any(row["failures"] or row["expected_complete"] != row["actual_complete"]
               for row in report["packets"]):
        lines.append("No discrepancies.")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Evaluate extraction offline on synthetic packets")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=Path("evaluation-results"))
    args = parser.parse_args()
    report = evaluate(args.dataset)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "report.md").write_text(markdown(report))
    print(f"Evaluated {report['packet_count']} packets ({report['dataset_version']})")
    print(f"Reports: {args.output / 'report.json'} and {args.output / 'report.md'}")


if __name__ == "__main__":
    main()
