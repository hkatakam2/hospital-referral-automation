# Opt-in Gemini workflow verification

Recorded November 4, 2026 for implementation commit `ca4d7cc`.
The [machine-readable summary](gemini-workflow-2026-11-04.json) retains counts,
execution identity, request timing, source fingerprint, limitations, and local
evidence locations without credentials or raw provider responses.

## Default verification suite

The repository verification skill passed on the combined implementation worktree
based on `05ba2c8`, before committing `ca4d7cc`. Pre-existing documentation edits
were present; this is not a claim of testing a clean checkout. The source
fingerprint remained identical before and after verification.

- 203 backend tests passed against owned isolated PostgreSQL databases.
- Ruff, ESLint, production build, and whitespace checks passed.
- 14 browser tests passed with no skips or failures.
- One separate real browser intake/correction/reload/API-readback journey passed.

The Gemini journey used the production adapter, API, PDF ingestion, assessment,
artifact persistence, evidence navigation, correction save and reload/readback.
Its default provider transport was a deterministic stub. This proves the local
workflow, not compatibility with Google. A subsequent browser POST was deliberately
mocked as a timeout to check draft/prior-result retention without retry. Backend
failure checks separately exercised the actual adapter with mocked provider HTTP.
The connection-release test asserted zero checked-out connections during provider
IO and uploaded another document during that call; saved source links retained
only the original input set. Existing atomic-save rollback checks passed.

## Separate live Gemini journey

The same browser journey passed with explicit live provider mode and one external
request using only this synthetic narrative:

> Avery Morgan, born 1974-03-12, was referred by Lakeside for cardiology.
> The reason for referral is Palpitations.

The application recorded `gemini-claims/1`, model and returned revision
`gemini-3.8-flash`, prompt `referral-claims/1`, evidence checks `literal-source/1`,
and checklist `five-required-fields/2`. All five candidates passed shared checks;
all five fields were found. Recorded provider request time was approximately
10.542 seconds. The browser test passed in 12.4 seconds, with 16.1 seconds for
startup and the suite. Cost is unknown because no explicit pricing was supplied.

The coordinator selected Gemini after seeing the external-processing notice,
ran extraction, opened source evidence, copied a DOB candidate while retaining a
manual name draft, and explicitly saved corrections. Reload and production GET
readback confirmed the saved correction and unchanged extraction snapshot, with
one historical run. The later mocked timeout did not make another provider call.

Both stub and live desktop/mobile screenshots were visually inspected. The
390px mobile checks found no horizontal overflow. The method selector returns to
Rules after reload; the selected historical run still identifies Gemini and its
recorded provenance.

## Limits and reproduction

This is one integration example, not a quality evaluation, clinical validation,
prompt-injection guarantee, load test, or durable-job recovery test. Literal source
support does not establish semantic correctness. Failed attempts are not persisted,
requests remain synchronous, and repeated submissions are not deduplicated.
The synthetic databases and original-file storage were isolated and cleaned up by
the harness; development data and local Gemini enablement were unchanged.

See the [README](../../README.md#opt-in-gemini-extraction) for the explicit live
command and configuration, the [feature map](../../.agents/skills/verify-hospital-referrals/features/extraction.md)
for coverage, and the [evaluation guide](../../backend/app/evaluation/README.md)
for versioned quality comparisons. Screenshots/traces and the full verifier report
remain in local temporary directories listed in the JSON summary; those paths
are evidence locations on the test machine, not portable download links.
