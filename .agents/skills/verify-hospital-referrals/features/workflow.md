# Coordinator workflow

## Implemented API behavior

POST `/api/referrals/{id}/information-requests`, POST `/resume-review` and GET
`/review-events` record and recover missing-information requests and explicit review
resumption. Referral list/detail responses include status and workflow version.
Sources: `backend/app/api/workflow.py`, `services/referral_workflow.py`,
`repositories/workflow.py`, `models/review_event.py`, and migration `0005`.

Run the full helper with `verify.py run` (there is no `--feature workflow` selector).
`backend/tests/test_workflow.py` uses real migrated PostgreSQL/API requests to cover
transitions, history ordering, reconnection, extraction scoping, immutable snapshots,
validation, legacy migration defaults without invented history, concurrent requests,
and rollback after a simulated commit failure. The commit failure is injected;
other reads/writes use actual database transactions. Existing persistence tests
check downgrade/rebuild and schema drift. Reconnection is not an OS restart check.

## Boundaries

History covers workflow actions, not field corrections. Reviewer names are supplied
unauthenticated demo identities. Requests are stored locally without email delivery.
No approval, OCR or automatic request closure is implemented. Uploads, extractions
and corrections leave workflow status unchanged. History is append-only through the
application API, not an immutable database ledger. Stale expected versions and invalid
transitions return 409; clients should read current referral/history before retrying.

## Browser workflow

Open a referral's Coordinator workflow panel. Enter the supplied demo reviewer,
requested information and reason; optionally link the selected extraction. Record
the request, then explicitly Resume review after follow-up. Refresh workflow reads
status/history after an interrupted response or conflict; it never repeats writes.
The inbox displays the saved status. Unsaved corrections survive workflow writes
and refreshes but remain local and are lost on navigation/reload.

`frontend/tests/review.spec.ts` has a real browser/API/PostgreSQL journey covering
request creation, selected extraction linkage, reload/readback, later PDF upload,
re-extraction and corrections leaving the request open, explicit resumption, immutable
historical extraction/events, referenced-run navigation and inbox status. It captures
workflow desktop/mobile screenshots and asserts no mobile horizontal overflow.
A second journey advances actual state through another API client to provoke a stale
browser conflict, then injects a history-only 503 after a real resume. It checks draft
retention, success despite read failure, and write counts during refresh recovery.
The 503 is a mocked read probe, not a database outage. All workflow writes are real.
