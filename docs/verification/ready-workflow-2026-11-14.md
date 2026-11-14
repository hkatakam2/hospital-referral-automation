# Administrative ready workflow verification — 2026-11-14

The full repository verification helper passed against base HEAD
`bdf4bd3760285aa1dd1a6274cdfa937abbe360ca` with this increment in the working tree.
The tree also contained pre-existing README/glossary edits and untracked AGENTS.md,
roadmap and architecture-skill files; this was not a clean-commit verification.
The report recorded matching source fingerprints before and after the run. Only
README/system-map prose corrections and this record were added after verification;
no application or executable-test changes followed the passing run.

Evidence directory (local, outside Git):
`/var/folders/rl/b87sjmhd2hlbw2l8xc1gnstw0000gn/T/referral-verification-mv06gasz`

Command: `python3 .agents/skills/verify-hospital-referrals/scripts/verify.py run`

- Backend: 267 tests passed against isolated migrated PostgreSQL.
- Browser: 20 tests passed, zero skipped, flaky or unexpected outcomes.
- Separate real-browser intake journey: 1 passed.
- Ruff, ESLint, production build and whitespace checks passed.
- The helper reported no unverified checks and released its owned server ports.
- New ready desktop/mobile screenshots were visually inspected. Ready status,
  locked editing controls, reviewed version and reopening/history controls were
  legible without overlap; the mobile journey also asserted no horizontal overflow.

The new real browser journeys uploaded a synthetic PDF, ran Rules, inspected source
evidence, blocked readiness with an unsaved draft, saved a correction, marked ready,
reloaded and read back the decision, checked inbox status, reopened, and attached
another document. API readback confirmed the earlier decision and extraction were
unchanged. A concurrent API correction provoked a real stale-version conflict;
refresh preserved the draft and required comparison with refreshed saved values.

The new backend cases cover incomplete/conflicting/partial packets, stale/foreign
runs, changed attachments, version checks, explicit request resumption, validation,
ready-state editing blocks, concurrent ready commands, status recheck for an upload
already parsing when readiness is recorded, retained decision context, reconnection,
migration/schema checks and refusal of lossy downgrade. Commit failure is injected
to verify rollback; it is not a real database outage. The browser history-only 503
is mocked after a real committed ready action; refresh does not duplicate writes.

All data is synthetic. Gemini uses deterministic stub HTTP in the default suite;
no live provider compatibility or quality claim is made. This records an
administrative decision using supplied demo reviewer names. Authentication,
clinical approval, OCR and downstream transmission are outside this increment.
