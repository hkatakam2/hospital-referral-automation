# Rule-based extraction and history

## Sub-features

Explicit extraction across current documents; five fields with candidates and exact document/page evidence; missing/invalid/conflicting findings; completeness and partial-source warnings; immutable saved runs and lightweight history listing.

Sources: `frontend/src/components/ExtractionPanel.tsx`, `hooks/useReferralWorkspace.ts`, `backend/app/api/extractions.py`, `services/referral_extraction.py`, `services/completeness.py`, `extraction/rule_based.py`, `repositories/extractions.py`.

## How to get to it (user POV)

Open a referral, upload a readable PDF, select Run extraction, and inspect Extraction review. Choose Extraction run to inspect an older result. Refresh history recovers saved runs without creating a new one.

## Driving it with Playwright

Run `verify.py run --feature extraction`. `frontend/tests/review.spec.ts` uses a real complete packet, sees all five fields found, then uploads a conflicting DOB document. The old run reports changed documents across reload; a new run shows conflicting candidates. Selecting the previous run restores its original findings. A partial packet shows missing fields and coverage warnings.

`backend/tests/test_extractions.py` covers the three ground-truth text fixtures, aliases/normalization, repeated evidence, invalid dates/specialties, unknown/missing values, cross-document conflicts, scope isolation, snapshot immutability, failed commits, history ordering/ties, empty history and 404/422.

## Gotchas

Rules recognize labeled lines, ISO dates, and cardiology aliases only. Manual referral data never fills extraction gaps. Missing/disputed values remain unselected; invalid candidates take finding precedence and stay visible. All five found plus readable-page coverage is the prototype checklist, not clinical or administrative approval. New attachments do not mutate old runs. Every POST creates a new run. No LLM or configurable institutional policy engine is present.
