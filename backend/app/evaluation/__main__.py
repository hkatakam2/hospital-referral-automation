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
from app.evaluation.execution import Pricing, execution_record, write_artifact
from app.evaluation.scoring import score_packet, summarize
from app.extraction.assessment import REQUIRED_FIELDS, assess_sources
from app.extraction.base import Extractor
from app.extraction.llm import GeminiSettings, LLMExtractionError, LLMExtractor
from app.extraction.rule_based import RuleBasedExtractor


def evaluate(
    dataset_path: Path,
    extractor: Extractor | None = None,
    *,
    artifact_dir: Path | None = None,
    pricing: Pricing | None = None,
) -> dict:
    dataset = load_dataset(dataset_path)
    extractor = extractor if extractor is not None else RuleBasedExtractor()
    if artifact_dir is not None:
        artifact_dir.mkdir(parents=True, exist_ok=False)
    rows = []
    timings = []
    checklist_version = None
    for index, packet in enumerate(dataset.packets):
        start = perf_counter()
        try:
            assessment = assess_sources(extractor, packet.sources)
        except LLMExtractionError as error:
            write_artifact(artifact_dir, index, packet.id, error.execution, error=str(error))
            raise
        timings.append((perf_counter() - start) * 1000)
        write_artifact(artifact_dir, index, packet.id, assessment.execution)
        checklist_version = assessment.checklist_version
        row = score_packet(packet, assessment)
        row["execution"] = execution_record(assessment.execution, pricing)
        rows.append(row)
    return {
        "report_schema_version": 2,
        "dataset_version": dataset.version,
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "extractor_version": extractor.version,
        "checklist_version": checklist_version,
        "python_version": platform.python_version(),
        "packet_count": len(rows),
        "overall": summarize(rows),
        "by_field": {field: summarize(rows, field) for field in REQUIRED_FIELDS},
        "by_document_type": {
            kind: summarize([row for row in rows if row["document_type"] == kind])
            for kind in sorted({row["document_type"] for row in rows})
        },
        "latency_ms": {
            "scope": (
                "One in-process extraction plus assessment per packet; "
                "no warmup, dataset IO or scoring; includes provider IO when selected"
            ),
            "samples": len(timings),
            "mean": statistics.mean(timings),
            "p50": statistics.median(timings),
            "p95": sorted(timings)[math.ceil(len(timings) * 0.95) - 1],
            "min": min(timings),
            "max": max(timings),
        },
        "execution": {
            "source_checks": {
                key: sum(row["execution"]["source_checks"].get(key, 0) for row in rows)
                for key in ("checked", "rejected")
            } if any(row["execution"]["source_checks"] for row in rows) else None,
            "pricing": pricing.model_dump() if pricing else None,
            "estimated_total_cost": (
                sum(row["execution"]["estimated_cost"] for row in rows)
                if all(row["execution"]["estimated_cost"] is not None for row in rows)
                else None
            ),
            "request_ms": [row["execution"]["request_ms"] for row in rows],
        },
        "packets": rows,
    }


def display(metric: dict) -> str:
    rate = metric["rate"]
    label = "N/A" if rate is None else f"{rate:.1%}"
    return f"{label} ({metric['numerator']}/{metric['denominator']})"


def markdown(report: dict) -> str:
    lines = [
        "# Extraction baseline",
        "",
        f"Dataset: `{report['dataset_version']}` ({report['packet_count']} packets)",
        "",
        f"SHA-256: `{report['dataset_sha256']}`",
        "",
        f"Extractor: `{report['extractor_version']}`; "
        f"checklist: `{report['checklist_version']}`; Python: `{report['python_version']}`.",
        "",
        "This curated source-text challenge set does not estimate clinical performance. "
        "See the evaluation README for scoring rules and limits.",
        "",
        "## Overall",
        "",
        "| Metric | Result (numerator/denominator) |",
        "| --- | --- |",
    ]
    for name, metric in report["overall"]["metrics"].items():
        lines.append(f"| {name} | {display(metric)} |")
    for title, key in (("By field", "by_field"), ("By document type", "by_document_type")):
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| Group | Value precision | Value recall | Exact match | Finding accuracy |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for name, summary in report[key].items():
            metrics = summary["metrics"]
            cells = [
                display(metrics[k])
                for k in (
                    "value_precision",
                    "value_recall",
                    "exact_match_accuracy",
                    "finding_accuracy",
                )
            ]
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
    execution = report.get("execution")
    if execution:
        lines.extend(
            [
                "",
                "## Execution",
                "",
                "Estimated total cost: " + str(execution["estimated_total_cost"]),
                "",
                "Pricing assumptions (per million tokens): `"
                + json.dumps(execution["pricing"])
                + "`.",
                "",
                "Unknown cost is null; estimates include reported thinking tokens. "
                "Per-packet model, prompt, usage and request timing are in report.json.",
                "",
                "Source checks: `" + json.dumps(execution["source_checks"]) + "`. "
                "These test source locations and literal support, not semantic entailment.",
            ]
        )
    latency = report["latency_ms"]
    lines.extend(
        [
            "",
            "## Processing latency",
            "",
            latency["scope"] + ".",
            "",
            f"{latency['samples']} samples; mean {latency['mean']:.3f} ms; "
            f"p50 {latency['p50']:.3f} ms; p95 {latency['p95']:.3f} ms. "
            "Timing varies by machine and run.",
            "",
            "## Failure examples",
            "",
        ]
    )
    for row in report["packets"]:
        if not row["failures"] and row["expected_complete"] == row["actual_complete"]:
            continue
        lines.extend(
            [
                f"### {row['packet_id']} ({row['document_type']})",
                "",
                f"Complete: expected `{row['expected_complete']}`, "
                f"actual `{row['actual_complete']}`.",
                "",
            ]
        )
        for failure in row["failures"]:
            # JSON quoting preserves whitespace and prevents fixture text altering Markdown.
            details = json.dumps(failure, ensure_ascii=True)
            lines.extend(["```json", details, "```", ""])
    if not any(
        row["failures"] or row["expected_complete"] != row["actual_complete"]
        for row in report["packets"]
    ):
        lines.append("No discrepancies.")
    return "\n".join(lines) + "\n"


def main():
    from pydantic import ValidationError

    parser = argparse.ArgumentParser(
        description="Evaluate synthetic extraction (rules or live Gemini)"
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=Path("evaluation-results"))
    parser.add_argument("--extractor", choices=["rules", "gemini"], default="rules")
    parser.add_argument("--input-price-per-million", type=float)
    parser.add_argument("--output-price-per-million", type=float)
    parser.add_argument("--cached-input-price-per-million", type=float)
    args = parser.parse_args()
    supplied = [args.input_price_per_million, args.output_price_per_million]
    pricing = None
    if any(value is not None for value in supplied + [args.cached_input_price_per_million]):
        if any(value is None for value in supplied):
            parser.error("Supply both input and output prices")
        try:
            pricing = Pricing(
                input_per_million=supplied[0],
                output_per_million=supplied[1],
                cached_input_per_million=args.cached_input_price_per_million,
            )
        except ValidationError:
            parser.error("Prices must be finite nonnegative numbers")
    extractor = RuleBasedExtractor()
    artifact_dir = None
    if args.extractor == "gemini":
        try:
            extractor = LLMExtractor(GeminiSettings())
        except ValidationError as error:
            fields = ", ".join(str(item["loc"][0]) for item in error.errors())
            parser.error("Invalid Gemini configuration: " + fields)
        if args.output.exists():
            parser.error("Gemini output directory must be new to prevent stale success reports")
        artifact_dir = args.output / "artifacts"
    try:
        report = evaluate(args.dataset, extractor, artifact_dir=artifact_dir, pricing=pricing)
    except LLMExtractionError as error:
        parser.exit(1, str(error) + "; partial artifacts retained; no quality report published\n")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "report.md").write_text(markdown(report))
    print(f"Evaluated {report['packet_count']} packets ({report['dataset_version']})")
    print(f"Reports: {args.output / 'report.json'} and {args.output / 'report.md'}")


if __name__ == "__main__":
    main()
