# Referral intake

## Sub-features

List registered referrals; create a cardiology referral with five required fields; open it directly; correct supplied fields without overwriting unrelated values. API supports POST/GET `/api/referrals`, GET/PATCH `/api/referrals/{id}`.

Sources: `frontend/src/pages/ReferralInboxPage.tsx`, `components/ReferralForm.tsx`, `pages/ReferralDetailPage.tsx`, `backend/app/api/referrals.py`, `schemas/referral.py`, `repositories/referrals.py`.

## How to get to it (user POV)

Open `/referrals`. Enter Patient name, Date of birth, Referring organization, Requested specialty (Cardiology), and Referral reason. Select Create referral. Use the inbox link to open existing records.

## Driving it with Playwright

Run `verify.py run --feature intake`. The skill's `scripts/live.spec.cjs` fills the actual labels, clicks Create referral, observes the generated UUID route and heading, GETs the saved referral, corrects its name, reloads, and finds it in the inbox. API attachments and before/after screenshots retain proof.

`frontend/tests/referrals.spec.ts` checks changed-field-only PATCH, failed-save draft retention, and navigation races with mocked endpoints. `backend/tests/test_referrals.py` covers real database-backed validation, trimming, null/blank rejection, ISO date/future-date handling, cardiology restriction, unknown properties, 404/422, stable list order, and update semantics. `test_health.py` covers health and CORS.

## Gotchas

All five fields are required before attaching a document. Creation is registration, not approval. There is no pagination, field-correction audit history, or document-first draft. The inbox displays persisted workflow status; workflow actions have separate history (see [workflow.md](workflow.md)). Mocked browser tests alone do not establish that creation or correction reached PostgreSQL. Native browser validation can stop a submission before FastAPI responds; API tests cover the backend boundary independently.
