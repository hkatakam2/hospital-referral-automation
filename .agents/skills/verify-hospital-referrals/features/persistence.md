# Persistence, restart recovery, and failure boundaries

## Sub-features

Retain referral corrections, original PDFs, page text, and extraction snapshots across connections/restarts; bootstrap an empty isolated database through Alembic; preserve scoping and transaction rollback behavior.

Sources: `backend/app/database.py`, `models/`, `repositories/`, `services/`, `alembic/`, `backend/tests/conftest.py`, `backend/tests/browser_server.py`, `frontend/playwright.config.ts`.

## How to get to it (user POV)

Create, upload, extract, and correct a referral. Reload or reopen its URL to recover saved values and latest history. A backend restart should retain the stored document and extraction IDs and payloads when the same database/storage are used.

## Driving it with Playwright

Run `verify.py run --feature persistence`. Real browser journeys prove reload recovery. `backend/tests/test_document_restart.py` starts one real Uvicorn process, creates a referral/document/extraction through HTTP, stops it, starts another against the same isolated storage/database, and compares saved document/extraction payloads and original bytes. Its API uses a reserved ephemeral socket, independent of the fixed browser ports.

`test_persistence.py` checks fresh connections, migrated empty database downgrade/rebuild, schema drift, retention through the document migration, and database-constraint/session rollback. Document/extraction suites (included by `--feature all`) cover failed promotion/insert/commit cleanup and immutable snapshots. Backend JUnit and retained logs are the proof for these checks; browser reload alone is not process-restart proof.

## Gotchas

PostgreSQL metadata/text and filesystem originals must both be retained. There is no backup or crash reconciliation service. Test databases are randomly named and owned by each harness; never downgrade/truncate the configured development database to verify migrations. The process-restart test explicitly reads back documents and extraction; referral correction persistence is separately checked across fresh connections and browser reload. Do not claim a dedicated corrected-referral process-restart assertion unless one is added and run.
