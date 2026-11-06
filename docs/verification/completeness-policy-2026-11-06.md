# Configurable completeness policy verification

Recorded November 6, 2026 for implementation commit `706794b`.
The [machine-readable summary](completeness-policy-2026-11-06.json) retains
command outcomes, source fingerprints, counts and local evidence paths.

The full verification helper passed against the combined implementation worktree
based on `17b9b7e`, including pre-existing documentation changes. This is not a
claim of verification on a clean checkout. Source fingerprints were identical
before and after the run; no product code changed after verification.

- 217 backend tests passed against isolated PostgreSQL databases.
- Ruff, ESLint, production build and whitespace checks passed.
- 15 browser checks passed, with no failures, skips or flaky results.
- One independent real intake/correction/reload/API-readback journey passed.

The policy backend checks use real startup configuration, PDF ingestion, API and
database storage. Changing a policy file does not change a running application's
captured definition. Starting a new application lifespan picks up the new policy;
the same source findings can satisfy fewer configured requirements while earlier
snapshots and corrections remain independent. Saved policy definitions/outcomes
survive readback. Legacy JSON without policy metadata remains readable. Invalid
configuration, optional invalid fields and mandatory source coverage are covered.
The retained rule-baseline aggregate comparison remains identical.

The real browser review journey asserts default policy identity and required
labels before and after reload. A separate mocked-detail rendering probe shows
one required field and four optional missing fields alongside a satisfied checklist.
That probe does not establish custom-policy persistence; the backend checks do.
Both default and optional-policy desktop/mobile screenshot pairs were visually
inspected, and both 390px overflow assertions passed.

The default Gemini transport is deterministic; no live provider request was made.
The independently named `live` helper is a real local intake journey, not live
Gemini. Development data and local configuration were not modified. This does not
verify custom-policy changes across an OS process restart, institutional policies,
document-type requirements, approvals or OCR. Existing default-policy process
restart and transaction rollback coverage remains part of the full suite.

Screenshots, traces and the full report remain in the local temporary evidence
directory recorded in the summary; those paths are not portable download links.
See the [README](../../README.md#configurable-completeness-checklist) for setup and
[feature coverage](../../.agents/skills/verify-hospital-referrals/features/extraction.md)
for real versus mocked boundaries.
