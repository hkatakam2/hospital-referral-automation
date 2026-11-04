# First live Gemini comparison

Recorded: 2026-11-04T04:21:21.585783+00:00

All 30 synthetic packets completed with `gemini-3.8-flash`, adapter
`gemini-claims/1`, prompt `referral-claims/1`, and checklist `five-required-fields/2`.
The provider returned model version `gemini-3.8-flash` for every packet. This is
one observed run on the existing challenge set, not held-out or clinical performance.

| Metric | Rule baseline | Gemini |
| --- | --- | --- |
| value_precision | 99.2% (125/126) | 98.5% (134/136) |
| value_recall | 91.2% (125/137) | 97.8% (134/137) |
| exact_match_accuracy | 92.0% (138/150) | 98.0% (147/150) |
| finding_accuracy | 92.7% (139/150) | 98.7% (148/150) |
| evidence_precision | 100.0% (144/144) | 100.0% (153/153) |
| evidence_recall | 93.5% (144/154) | 99.4% (153/154) |
| false_completeness_rate | 0.0% (0/15) | 0.0% (0/15) |

## Differences to review

- `empty-dob`: Gemini omitted the blank DOB claim, producing missing instead of the annotated invalid finding.
- `us-format-dob`: the adapter conservatively rejected `03/12/1974` as ambiguous; the annotation specifies US format.
- `narrative-letter` and `narrative-missing-organization`: selected referral reasons used `recurrent palpitations` while annotations specify `Recurrent palpitations`. These count as two incorrect selections under unchanged exact scoring.

No labels, prompts, normalization rules, or scoring were adjusted after this run.
Alternate-format recall improved from 19/25 to 24/25; narrative recall improved
from 3/9 to 7/9. Precision decreased slightly because both case differences count
as false positives and false negatives. All 148 returned claims passed literal
source-location/source-value checks; this does not establish semantic entailment.

## Timing and usage

Mean extraction plus assessment: 7.832 seconds; p50: 7.740 seconds; p95: 11.932
seconds. The rule baseline mean was 0.174 milliseconds. Gemini timing includes
provider network IO; this is not a controlled speed benchmark.

Provider totals: 9,697 prompt tokens, 13,182 candidate tokens, 16,700 thinking
 tokens, and 39,579 total tokens. No cached input tokens were reported.
Cost remains unknown because explicit pricing was not supplied; it is not zero.

## Execution and retained evidence

The configured process had a stale `GEMINI_API_KEY` that overrode `backend/.env`.
The successful run loaded that file with `load_dotenv(".env", override=True)`
before invoking the evaluator. No key or environment file is committed.
For normal shell use with a key stored in `.env`, remove the stale override:

```sh
cd backend
env -u GEMINI_API_KEY .venv/bin/python -m app.evaluation \
  --extractor gemini --output evaluation-results/gemini-new-run
```

The output directory must be new. Model output, usage and latency can vary.
Raw provider responses remain outside Git in
`/private/tmp/referral-gemini-live-20261104-3/artifacts/` (30 packet artifacts).
The committed JSON and Markdown retain quality counts, packet discrepancies,
execution configuration, model/prompt versions, usage and timing. Dataset checksum
matches the committed rules baseline. Browser/API extraction remains rules/1.
