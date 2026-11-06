# Rules, opt-in Gemini extraction, and history

## Sub-features

Explicit extraction across current documents; five fields with candidates and exact document/page evidence; missing/invalid/conflicting findings; completeness and partial-source warnings; immutable saved runs and lightweight history listing.

Sources: `frontend/src/components/ExtractionPanel.tsx`, `hooks/useReferralWorkspace.ts`, `backend/app/api/extractions.py`, `services/referral_extraction.py`, `extraction/assessment.py`, `extraction/rule_based.py`, `repositories/extractions.py`.

## How to get to it (user POV)

Open a referral, upload a readable PDF, select Run extraction, and inspect Extraction review. Choose Extraction run to inspect an older result. Refresh history recovers saved runs without creating a new one.

## Driving it with Playwright

Run `verify.py run --feature extraction`. `frontend/tests/review.spec.ts` uses a real complete packet, sees all five fields found, then uploads a conflicting DOB document. The old run reports changed documents across reload; a new run shows conflicting candidates. Selecting the previous run restores its original findings. A partial packet shows missing fields and coverage warnings.

`backend/tests/test_extractions.py` covers the three ground-truth text fixtures, aliases/normalization, repeated evidence, invalid dates/specialties, unknown/missing values, cross-document conflicts, scope isolation, snapshot immutability, failed commits, history ordering/ties, empty history and 404/422.

Assessment checks exercise empty and incomplete extractor outputs, all five required fields, selected-value/finding consistency, invalid precedence, and rejection of unknown fields. An integration check persists an empty extractor result and reads back five missing findings with `complete=false`. Browser checks cover explicit retry after a mocked write failure, successful writes followed by failed list/history refreshes without duplicate writes, and late extraction responses. These failure probes mock only the indicated frontend requests; successful writes and their readback use the real backend.

## Gotchas

Rules recognize labeled lines, ISO dates, and cardiology aliases only. Manual referral data never fills extraction gaps. Missing/disputed values remain unselected; invalid candidates take finding precedence and stay visible. The configured required fields found plus readable-page coverage is the prototype checklist (all five by default), not clinical or administrative approval. New attachments do not mutate old runs. Every POST creates a new run. The browser/API defaults to rules/1; explicitly enabled Gemini is selected per run.
Offline quality evaluation is mapped in [evaluation.md](evaluation.md); only fictitious field requirements are configurable, not institutional or document-type rules.

## Shared evidence boundary and provenance

`extraction/assessment.py` validates all adapters against exact source document/page/quote and raw-value support, and checks selected-value normalization before selection. `test_evidence_verification.py` injects faulty adapters to reject missing citations, wrong document/pages, fabricated/blank quotes, invented values and unrelated instruction-like text. The rule-baseline aggregate counts must remain identical. Literal checks do not establish semantic entailment or prompt-injection resistance.

`test_extraction_provenance.py` injects the actual Gemini adapter with mocked HTTP transport into the persistence service. It verifies original structured claims, pre-assessment candidates, raw response and execution metadata are saved separately from the public snapshot. Detail responses expose an allowlisted provenance summary; history omits it. This is local adapter/persistence proof, not live provider compatibility.

## Opt-in Gemini workflow

`GET /api/extraction-methods` reports local configuration availability without
provider IO. POST accepts rules/gemini, preserves the empty-body Rules default,
and enforces GEMINI_ENABLED in the backend. `test_extraction_methods.py` uses the
production Gemini adapter with MockTransport through real API/database operations:
availability, invalid settings, unsupported claims, timeout/transport/HTTP/blocked/
malformed/oversized failures, one request/no retry, prior-run retention, private
content exclusion, zero checked-out connections during provider IO, and a document
attached during processing excluded from the saved fixed input set.

The Gemini workflow browser journey uses real PDF upload, method selection, API,
assessment, storage, evidence navigation, correction save, and reload/API readback.
Default Playwright mode installs `tests/gemini_browser_stub.py` only in the isolated
test server, supplying deterministic provider HTTP to the real adapter. It makes
no Google requests and is not model-quality evidence. A separate mocked POST
failure within that journey checks prior-result/draft retention without retry.
Availability probes mock discovery failure/disabled responses. Screenshots cover
the Gemini controls at desktop/mobile widths and need visual inspection.

Live mode is explicitly selected with REFERRAL_TEST_GEMINI_MODE=live; see the
README command. Record its result separately. Requests remain synchronous and
failed attempts are not persisted; no worker, idempotency, or automatic fallback.

## Configurable field completeness

One validated JSON policy is captured at server startup. All five fields still get
source checks and findings; required fields must be found and readable source
coverage is mandatory. `backend/tests/test_policy.py` exercises actual startup,
PDF upload, production API and PostgreSQL: a config edit has no effect until a new
lifespan starts, then new runs use changed requirements while earlier runs and
field findings stay unchanged. Corrections do not rewrite either snapshot. Tests
cover malformed/missing configuration, unknown/duplicate/empty requirements,
immutable configuration, invalid optional fields, partial/no sources, and legacy
JSON without policy metadata. This startup-lifespan check is not a dedicated OS
process-restart check with changing policy files.

The real browser review journey asserts saved default policy identity and five
required labels before/after reload. A separate mocked-detail browser probe shows
one required and four optional/missing fields with a satisfied checklist, captures
desktop/mobile screenshots and checks overflow. That probe proves rendering only;
custom-policy persistence is proven by the real backend/API check above. There is
no browser policy selector, rule language, document-type requirement, or approval.
