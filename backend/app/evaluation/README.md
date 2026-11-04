# Extraction quality evaluation

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

## Scoring contract (report schema 2)

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
runs; rule-based quality output is repeatable with the same dataset, code and Python version.
Live model output and token usage may vary between requests.
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
scoring path. The CLI selects rules by default and Gemini explicitly. Keep this
challenge set version fixed when comparing extractors; do not rewrite ground truth
to improve a score. The 30 packets intentionally share synthetic identities and
exercise known failure modes: results are not statistical estimates for hospital
traffic. Future model tuning needs a separate held-out set to avoid overfitting.


## Gemini comparison

Install backend runtime dependencies from `backend/` with `.venv/bin/python -m pip install -e '.[dev]'`.
Set `GEMINI_API_KEY` and `GEMINI_MODEL` in `backend/.env` or the process environment.
No model is silently selected. Use a model available to your key that supports
`generateContent` structured output. Never put the key in CLI arguments or reports.
The rules command remains network- and credential-free.

From `backend/`:

```sh
.venv/bin/python -m app.evaluation --extractor rules --output evaluation-results/rules
.venv/bin/python -m app.evaluation --extractor gemini --output evaluation-results/gemini-run-1
```

The Gemini command sends synthetic page text to Google's Gemini API and can incur
usage charges. It makes one sequential request per packet (30 requests for version 1).
The output directory must be new. It retains `artifacts/0000.json` etc. containing
packet IDs, original provider responses, execution configuration, versions, usage,
request timing and failure details. Artifact filenames use indexes, not packet IDs.
A failed packet aborts the run with a nonzero exit status; completed and failed
attempt artifacts remain, and no aggregate quality report is published. There are
no automatic retries, fallback to rules, truncation of input, or dropped packets.
Inspect a failure before making a new run; earlier calls may already have incurred cost.

Settings: `GEMINI_TIMEOUT_SECONDS` (per HTTP phase, default 60, maximum 300),
`GEMINI_MAX_INPUT_CHARS` (serialized packet bound, default 100000), and
`GEMINI_MAX_OUTPUT_TOKENS` (default 8192). Oversized packets fail before any request;
blocked, malformed, truncated, or incomplete responses fail explicitly.

Pricing is optional and never guessed. Supply current USD prices per million tokens:

```sh
.venv/bin/python -m app.evaluation --extractor gemini \
  --output evaluation-results/gemini-priced-1 \
  --input-price-per-million 0.10 --output-price-per-million 0.40
```

These numbers illustrate the flags; they are not a statement of Gemini pricing.
Cost estimates apply the input rate to uncached prompt tokens and the output rate
to candidate plus reported thinking tokens. If cached tokens occur, supply
`--cached-input-price-per-million` too. Missing prices or required usage produce
`null`, including the total if any packet cost is unknown. Estimates exclude taxes,
other service charges, and pricing tiers; record the applicable rates for the chosen
model/context size yourself. JSON retains each packet's provider usage separately.

The report preserves existing quality counts and exact evidence scoring. Schema 2
adds per-packet execution metadata and aggregate cost/source checks. Latency includes
provider IO for Gemini but excludes artifact writes and scoring; request-only timing
is separate. Compare overall, per-field and per-document-type quality against
`reports/extraction-baseline-v1/report.json`; historical schema 1 remains unchanged.
Do not tune prompts on this challenge set and describe it as held-out performance.

## Claims, normalization, and grounding limits

The model returns five required candidate lists. Empty lists mean absent information;
multiple distinct values survive as conflicts. It cannot set findings, completeness,
validation issues, or selected values. Equivalent candidates combine evidence.
Application normalization preserves source text case and collapses whitespace;
cardiology aliases normalize as before. ISO dates retain rules/1 validation. Gemini
also accepts named-month dates and unambiguous US numeric dates where the day exceeds
12, only when the proposed ISO date agrees with deterministic parsing. Ambiguous
`03/12/1974` remains invalid even though the corpus annotates that fixture as US format.
This conservative policy is explicit; it does not change annotations or rules/1.

Every returned citation must identify an input document/page and quote an exact
substring. The claimed source value must occur in a supporting quote. Unsupported
claims remain visible as invalid candidates with no selected value. Source-check
counts are reported independently of exact annotation evidence agreement. These
checks do not establish semantic entailment: a real quote could describe someone
other than the patient. Instruction-like source text is treated as untrusted data
in the prompt, but prompting does not prove resistance to all prompt injection.

Raw responses remain separate from assessed fields and are excluded from public
API models. Browser/API extraction defaults to rules/1 and supports explicitly enabled Gemini;
see the root README for method selection and short database transaction scopes.
This CLI requires no database or server and ignores GEMINI_ENABLED.

Provider contract references: [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
and [generateContent API and usage metadata](https://ai.google.dev/api/generate-content).


## Retained live comparison

The first 30-packet Gemini run is retained in
[`reports/extraction-gemini-v1`](../../reports/extraction-gemini-v1/comparison.md).
It records the unchanged dataset/scoring contract, measured gains and regressions,
latency, usage, and the remaining normalization/finding discrepancies.

Gemini API-key precedence is explicit constructor argument, then `GEMINI_API_KEY`
in `backend/.env`, then the process environment. This prevents stale shell exports
from overriding a refreshed file key. If the file/key is absent, environment-only
configuration still works. An empty file key fails validation instead of silently
using another key. The file path is anchored to `backend/`, regardless of working
directory. Other Gemini settings retain environment-over-file precedence.
No process environment is modified, and no key is printed.
