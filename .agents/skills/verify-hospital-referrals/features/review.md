# Human evidence review and correction

## Sub-features

Show saved values separately from unsaved draft and extraction findings; navigate exact evidence; copy individual valid candidates; explicitly save corrections; retain draft on validation failure; recover independent panels and avoid obsolete read results.

Sources: `frontend/src/pages/ReferralDetailPage.tsx`, `components/ReferralForm.tsx`, `ExtractionPanel.tsx`, `SourceTextViewer.tsx`, `hooks/useReferralWorkspace.ts`, `api/client.ts`.

## How to get to it (user POV)

Open a referral with an extraction. View evidence opens and focuses its document/page and displays the quote. Use a candidate in correction copies just that field. Save corrections persists the draft. Unsaved corrections are marked on screen.

## Driving it with Playwright

Run `verify.py run --feature review`. The real review journey in `frontend/tests/review.spec.ts` observes focused source headings and quotes, preserves a manual name edit while copying a DOB candidate, saves/reloads, and reads the backend record to prove candidate copying alone does not persist. After saving a conflict choice, the original conflicting extraction finding remains unchanged. It captures desktop/mobile screenshots and checks mobile horizontal overflow.

The skill live journey independently proves browser form writes and reload/API readback. Existing mocked probes cover field-validation errors retaining a draft, isolated history failure/recovery, late referral responses, and late document responses. These mocks establish frontend behavior; they do not simulate a database outage.

Workspace write coordination lives in `useReferralWorkspace.ts`; document and extraction panels render its state and invoke explicit actions. Review probes also cover late extraction reads and recovery from failed refreshes after committed writes, with request counts and backend readback checking that refreshes never repeat writes.

## Gotchas

Correcting the referral does not resolve contradictory source documents or rewrite historical checklists. Invalid candidates have no apply action. Candidate copying is disabled while a correction save is pending. Workflow action history is separate (see [workflow.md](workflow.md)); API correction history is available; browser audit controls follow in the next increment. There is no approval action, clinical decision, or automatic save. Unsaved edits are local and are lost on leaving/reloading; the current UI shows a warning but has no navigation blocker. Screenshots need visual inspection before layout can be described as visually verified.

## Provenance and rejected candidates

Open Run provenance in Extraction review for shared check counts and any recorded provider/model/prompt identity. Rejected candidates show Cannot use this candidate and their reason; missing citations are explicit. Historical runs without provenance show an unavailable message. The real review journey asserts persisted rule provenance after extraction and reload, with desktop/mobile screenshots of the expanded panel. A separate mocked-detail browser probe verifies Gemini identity, rejection without a copy action, and absent historical metadata; it does not claim provider execution. The separate Gemini workflow journey drives the actual method selection and persisted review path with stub provider HTTP by default; explicit live mode uses Google. A mocked subsequent failure verifies that the previous result and unsaved correction draft remain visible.

## Policy review

Extraction review shows saved policy identity, mandatory source coverage, and
required/optional field labels. Missing historical definitions are explicit. The
real review journey covers default metadata and reload; the optional-field layout
probe mocks detail only (see extraction coverage) and needs screenshot inspection.
A satisfied checklist may still show optional invalid/conflicting/missing findings.

## Correction API persistence

`test_corrections.py` exercises real PostgreSQL changes/history, normalization, no-op
saves, required audit metadata, fresh connections, scoped reads, concurrent commands,
stale retry, injected commit failure rollback, and legacy migration/schema drift.
Corrections use a saved-values version separate from workflow version. Source snapshots
and workflow status remain unchanged. Reviewer names are supplied demo identities.
