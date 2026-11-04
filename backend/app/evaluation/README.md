# Offline extraction evaluation

From `backend/`, using the existing virtual environment:

```sh
.venv/bin/python -m app.evaluation --output evaluation-results
```

This runs `RuleBasedExtractor` through the same `assess_sources` function used by
persisted extraction. It reads the packaged `data/referrals-v1.json` and writes
`report.json` and `report.md`. No server, database, PDF parser, network, model API,
or credentials are required. `--dataset PATH` selects another dataset with the
same validated schema; `--output DIRECTORY` selects the report directory. Existing
report files in that directory are overwritten. Invalid datasets or extractor
errors fail the command; they are never silently excluded from denominators.

The JSON includes complete counts and metrics overall, by field, and by packet
document type; every packet's scores, expected/actual completeness, and all field
or evidence failures; dataset version and SHA-256; extractor/checklist versions;
Python version; and timing. Markdown includes aggregate tables and every failing
packet with its discrepancies. Document type denotes the packet's fixture category,
not a clinical taxonomy. Reports retain synthetic text only.

## Scoring contract (report schema 1)

Expected values and findings are authored independently of the extractor. See
[data/README.md](data/README.md) for annotation and normalization rules. Predictions
use assessment-selected values, not manually entered referral values or an oracle
selection from candidates. Scoring itself performs no fuzzy matching or additional
normalization. Different valid spellings still count as wrong unless annotations
and extractor already normalize them to the same string.

All aggregate rates are micro-averaged from counts, rather than averaging rates
across packets. Each metric records numerator, denominator, and rate. A zero
denominator produces JSON `null` and Markdown `N/A`, never a perfect score.

| Metric | Numerator | Denominator |
| --- | --- | --- |
| Value precision | Correct non-null selections (TP) | All non-null selections (TP + FP) |
| Value recall | Correct non-null selections (TP) | All expected non-null values (TP + FN) |
| Exact-match accuracy | Selected value equals expected value, including null/null | All field instances |
| Finding accuracy | Predicted finding equals expected finding | All field instances |
| Missing / conflicting / invalid precision | Correct predictions of that status | All predictions of that status |
| Missing / conflicting / invalid recall | Correct predictions of that status | All annotations of that status |
| Evidence precision | Exact expected evidence tuples returned | All distinct returned evidence tuples |
| Evidence recall | Exact expected evidence tuples returned | All distinct expected evidence tuples |
| False completeness rate | Predicted complete packets annotated incomplete | All annotated incomplete packets |
| Packet completeness accuracy | Predicted completeness equals annotation | All packets |

A wrong non-null value on an expected known field counts as both FP and FN. An
abstention on that field counts as FN only. An invented value on an absent,
invalid, or conflicting field counts as FP. Null/null counts toward exact-match
accuracy even when findings disagree; finding accuracy and status precision/recall
expose that distinction. Missing, invalid, and conflicting all have null selected
values but distinct expected findings. All five fields are required in version 1;
there are no not-applicable exclusions.

Evidence is a set of `(document_id, page_number, exact_quote)` tuples per field,
unioned across candidates. Duplicate identical tuples count once; evidence from
different documents/pages counts separately. Scoring requires the annotated quote
span exactly, so a valid alternative span may score poorly. This is a strict
annotation agreement measure, not semantic evidence entailment or production
verification. Field precision/recall measure selected values; candidate alternatives
are represented by findings and evidence rather than candidate-value accuracy.

A complete label requires five found fields and no textless pages, independent
of how easily the current extractor recognizes them. Correct fields in a partial
packet still cannot make it complete. False completeness measures that checklist
outcome, not value correctness, administrative approval, or clinical readiness.

Latency is one `perf_counter` sample per packet around extraction plus assessment,
excluding dataset loading, scoring, report generation, PDF parsing, and persistence.
The report gives sample count, mean, median, nearest-rank p95, minimum and maximum
in milliseconds. There is no warmup. This lightweight local timing varies between
runs; all other output is repeatable with the same dataset, code and Python version.
The underlying date validator uses today's UTC date, so all version 1 valid dates
are historical and the invalid cases avoid time-dependent future dates.

## Baseline and future comparisons

The committed baseline is in `backend/reports/extraction-baseline-v1/`. Reproduce
it from `backend/` with:

```sh
.venv/bin/python -m app.evaluation --output reports/extraction-baseline-v1
.venv/bin/pytest -q tests/test_evaluation_dataset.py tests/test_evaluation_scoring.py
.venv/bin/ruff check .
```

`evaluate(dataset_path, extractor=...)` also accepts an extractor implementing the
existing protocol, so future adapters can reuse exactly the same assessment and
scoring path. CLI currently selects only the deterministic extractor. Keep this
challenge set version fixed when comparing extractors; do not rewrite ground truth
to improve a score. The 30 packets intentionally share synthetic identities and
exercise known failure modes: results are not statistical estimates for hospital
traffic. Future model tuning needs a separate held-out set to avoid overfitting.
