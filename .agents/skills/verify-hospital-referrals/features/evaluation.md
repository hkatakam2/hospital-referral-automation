# Extraction quality and Gemini evaluation

Surface: `python -m app.evaluation` from `backend/`. Rules are the offline default;
`--extractor gemini` explicitly selects a live provider. No browser or database
is used by this command. Browser/API extraction remains rules/1.

Sources: `app/evaluation/__main__.py`, `execution.py`, `scoring.py`,
`app/extraction/base.py`, `llm.py`, `llm_schema.py`, `grounding.py`,
`normalization.py`, and `candidates.py` under `backend/`.

`tests/test_evaluation_dataset.py` validates the independently annotated corpus.
`tests/test_evaluation_scoring.py` checks explicit quality denominators, evidence
agreement, errors, reproducibility and the rules CLI. `tests/test_llm_extraction.py`
uses httpx MockTransport through the actual adapter: schema/header/payload,
missing/duplicate/conflicting claims, source-location rejection, normalization,
blocked/truncated/malformed responses, HTTP/transport errors without retries,
input limits, execution artifacts, cost and committed-baseline quality parity.
These tests prove local behavior, not live Gemini compatibility or quality.

A live check requires GEMINI_API_KEY and GEMINI_MODEL in backend/.env or the process
environment. Run `--extractor gemini --output /private/tmp/unique-new-directory`.
Retain report.json, report.md and packet artifacts; record model/prompt/dataset
versions. Compare quality against the committed baseline without changing labels.
A failed packet must not disappear from denominators; no quality report is published
on failure. Missing prices/usage mean unknown cost. Source checks are literal
location checks, not semantic entailment or administrative approval.

The verification helper's backend suite includes these mocked tests. Its browser
journeys verify the unchanged rule-based application, not Gemini. No live Gemini
request is made by pytest or the helper.
