---
name: verify-hospital-referrals
description: Verify the hospital-referral-automation application's implemented intake, PDF ingestion, rule-based extraction, evidence review, and persistence using isolated PostgreSQL and real browser journeys. Use when asked to verify this project, prove a workflow, or regression-check an implemented change.
---

# Verify Hospital Referrals

Verify observable behavior, retain proof, and distinguish product failures from unavailable checks. Scope is the implemented application through roadmap Level 6. OCR, policy configuration, audit history, approval, authentication, and document-first drafts are not implemented and must not become passing claims. Opt-in browser/API Gemini uses the production adapter with deterministic provider HTTP in the default browser harness. Live mode is explicit and billable; only a live credentialed run proves provider compatibility, and quality claims require the separate evaluator.

Use this skill from the repository root. Read [features/README.md](features/README.md) and the files relevant to the requested change before choosing checks. The feature map records user routes, source entry points, assertions, and coverage limits. Do not assume historical test counts remain current.

## Launch

Use the existing environments and harness; no dependency installs or service changes happen inside the helper.

```sh
python3 .agents/skills/verify-hospital-referrals/scripts/verify.py doctor
python3 .agents/skills/verify-hospital-referrals/scripts/verify.py run
```

`run` executes backend tests, Ruff, ESLint, production build, whitespace checks, the existing Playwright suite, and this skill's real browser intake journey. It prints a unique evidence directory outside the checkout. Use `--repo /absolute/checkout` from another directory. To narrow backend tests while retaining cross-feature browser coverage:

```sh
python3 .agents/skills/verify-hospital-referrals/scripts/verify.py run --feature documents
```

Allowed feature names: `intake`, `documents`, `extraction`, `review`, `persistence`, `all`. Default `all` is appropriate for a full current-functionality verification. A focused run is not full backend regression proof.

Prerequisites: `backend/.venv` with dev dependencies, `frontend/node_modules`, Playwright Chromium, local PostgreSQL with a test role able to create databases, and free loopback ports 8001/5174. Follow the repository README if setup is missing. Never print `.env` or DSNs. `TEST_DATABASE_URL`, when set, selects the dedicated PostgreSQL test server; otherwise tests derive their server from backend settings. Backend settings load from `backend/.env` because checks run in `backend/`.

The existing browser launcher creates a random `referral_test_browser_*` database, applies migrations, and serves FastAPI on 8001 with temporary original-PDF storage. Vite on 5174 proxies to that API. Readiness comes after migration completion. The backend pytest suite creates its own random `referral_test_*` database. No development database migrations, writes, or truncation are part of this skill.

## Doctor

`doctor` is a read-only preflight: check local tools, harness files, occupied ports, PostgreSQL connectivity, and CREATEDB privileges. It does not install, migrate, start services, or write evidence. Exit 0 means prerequisites are ready; exit 2 means blocked.

Playwright then owns startup and checks `/api/health` plus Vite readiness before driving. It refuses existing servers (`reuseExistingServer: false`). Do not attach the verifier to a user's running 8000/5173 session. If behavior is surprising, read `doctor.json`, the failing command log, and the trace; rerun doctor after owned processes have exited before another drive. A healthy endpoint alone does not establish correct UI behavior.

## Drive

The reusable control surface is Playwright, with stable labels/roles from the actual application. `scripts/live.spec.cjs` is run automatically by `verify.py run`; do not invoke it as a standalone Node script. It creates a referral via the real form, saves a correction, reloads, reads both records through production GET endpoints, and returns to the inbox. There are no mocked application endpoints in this journey.

The existing `frontend/tests/review.spec.ts` drives real PDF upload, extraction, candidates, evidence navigation, older runs, partial pages, and source-change warnings. `frontend/tests/referrals.spec.ts` also contains mocked validation and response-race probes. Treat those as focused frontend checks, not proof of real persistence. Backend tests separately verify file bytes/checksums, transaction failures, migration rebuilding, scoping, and real backend process restarts. Read the feature map for precise mappings and gaps.

For a new or changed path not represented in the map, exercise the actual UI/API, add an appropriate focused journey when warranted, and record what was observed. Do not weaken an assertion or use internal state setters just to obtain a pass. Ordinary verification reports defects; modifying product behavior or committing/publishing changes requires task authorization beyond verification.

## Evidence

A run retains `report.json`, `doctor.json`, command logs and exit codes, `backend.xml`, `browser.json`, `live.json`, screenshots, API-readback attachments, and Playwright traces. Every browser test is run with tracing enabled. For a durable user-chosen destination:

```sh
python3 .agents/skills/verify-hospital-referrals/scripts/verify.py run --evidence-dir /private/tmp/referral-proof-unique
```

The destination must be new and outside the checkout. The helper never deletes it. It records the tested HEAD, initial working-tree status, and before/after source fingerprints; source changes during a run prevent a passing report. HEAD plus a dirty worktree is not a verified clean commit.

After a passing run, inspect the relevant screenshots with an image-viewing tool and the test assertions/logs. Screenshots alone do not prove persistence; API/file/database readback and restart assertions provide that evidence. State separately which surfaces were visually inspected. Use `node frontend/node_modules/@playwright/test/cli.js show-trace /absolute/path/to/trace.zip` when a trace needs inspection.

Report scope, tested commit and dirty status, checks/counts actually run, failures or `unverifiedChecks`, and the concrete evidence directory. Exit 0 means executed checks passed, 1 means checks failed, and 2 means blocked/interrupted. A blocked doctor does not verify any workflow. Do not describe mocked paths, skipped future features, or an uninspected layout as proven.

## Cleanup

Playwright tears down only servers it launches. The browser server's `finally` drops its owned random database and removes temporary originals; pytest cleans its own database and storage. Evidence is outside both disposable areas and survives teardown. The helper checks that verification ports are free afterward; never kill a process merely by name or port.

On interruption, the helper signals only the subprocess group it started, allows graceful shutdown, and forces termination only if that group fails to exit. A hard kill can leave a test database. Inspect ownership before removing residue; never run `docker compose down -v`, truncate development tables, or delete unknown `referral_test_*` databases. Leave pre-existing services, user files, and untracked `docs/` intact.

## Maintain

When implemented routes, labels, persistence behavior, or harness commands change, update the matching feature file and re-drive that feature. Add new implemented features to the index; do not add roadmap promises as current behavior. Keep this skill project-local so its verification contract can evolve alongside the code.

The structure is adapted from [pstack's verification-skill specification](https://github.com/cursor/plugins/blob/main/pstack/skills/create-verification-skill/SKILL.md); the commands and invariants above are specific to this repository.
