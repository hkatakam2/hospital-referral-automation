# Hospital Referral Automation

FastAPI backend and React + TypeScript frontend, built with Vite.

## Requirements

- Python 3.11 or newer (use `python3.13` below if your default `python3` is older).
- Node.js 22.12+ (or 20.19+) and npm.
- Docker with Docker Compose v2, running locally.

## Run locally

Start PostgreSQL from the project root (Docker must be running). On a fresh
checkout, create the backend environment file first; keep an existing `.env`:

```sh
cp backend/.env.example backend/.env
docker compose --env-file backend/.env up -d --wait db
```

Only PostgreSQL runs in Docker. FastAPI and Vite run on your Mac. The Compose
service uses PostgreSQL 17, a localhost-only port, a readiness health check, and a
named volume. The example credentials are for synthetic local development.
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `POSTGRES_PORT` configure
Compose; `DATABASE_URL` configures FastAPI and Alembic. If you customize them,
update the URL to match (URL-encode special characters in credentials).
Changing these variables does not change users/passwords in an existing volume.

Start the backend from the project root:

```sh
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, start the frontend from the project root:

```sh
cd frontend
npm ci
cp .env.example .env
npm run dev
```

- Frontend: http://localhost:5173
- API health: http://127.0.0.1:8000/api/health
- Interactive API docs: http://127.0.0.1:8000/docs

The starter page checks the backend connection. Vite forwards `/api` requests to port 8000 during development. Edit `API_PROXY_TARGET` in `frontend/.env` if the backend runs elsewhere. Restart Vite after environment changes.

## Manual referral intake

Use only synthetic information. Open http://127.0.0.1:8000/docs and use
`POST /api/referrals` to register a referral with this request body:

```json
{
  "patient_name": "Avery Morgan",
  "date_of_birth": "1974-03-12",
  "referring_organization": "Lakeside Primary Care",
  "requested_specialty": "cardiology",
  "referral_reason": "Recurrent palpitations"
}
```

The API returns `201` with the submitted fields, a generated UUID in `id`, and a
UTC `created_at` timestamp. Copy the ID into `GET /api/referrals/{referral_id}`
in `/docs` to retrieve the record (`200`). An unknown UUID returns `404`; malformed
IDs and invalid request bodies return `422`.

All five fields are required. Text fields are trimmed and cannot be blank, date
of birth cannot be later than today's UTC date, and specialty must be exactly
`cardiology`. Unknown fields, including client-supplied IDs and timestamps, are
rejected. Creation registers information; it does not approve a packet or detect
conflicting documents.

Use `GET /api/referrals` to browse all registered referrals in creation order.
It returns `200` with a JSON array, or `[]` when no referrals exist. The list is
not paginated in this prototype.

To correct a saved record, use `PATCH /api/referrals/{referral_id}` in `/docs`.
For example, submit just the corrected date of birth:

```json
{
  "date_of_birth": "1974-03-21"
}
```

The response is `200` with the complete updated record. Omitted fields retain
their values; the ID and creation timestamp remain unchanged. Supplied fields
follow the creation validation rules: required fields cannot be cleared with
`null` or blank text, and unknown or server-managed fields are rejected. Invalid
updates return `422` and leave the record unchanged. An unknown UUID returns
`404`; a malformed ID returns `422`. An empty object is a no-op returning the
existing record. Corrections overwrite the current values; there is no audit
history yet.

To verify the manual workflow, create two synthetic referrals, list them, correct
one referral, and retrieve both to confirm only the intended record changed.
This completes manual intake with persistent PostgreSQL storage.

Referrals and corrections are stored in PostgreSQL and survive backend restarts.
List results are ordered by creation time, then UUID for equal timestamps.
The frontend still shows the connection page; use `/docs` for intake, listing,
inspection, and corrections. PDF upload and page-level text inspection are also
available through `/docs`, as described below.

Database tables are managed by Alembic; starting the API does not create them.
Run `alembic upgrade head` from `backend/` before using the referral endpoints.
The health endpoint checks the application only, not database readiness.
Database outages cause referral requests to fail; writes never fall back to memory.

From the project root, `docker compose stop db` stops PostgreSQL, and
`docker compose --env-file backend/.env up -d --wait db` starts it again.
`docker compose down` removes the container/network but keeps the named volume;
`docker compose down -v` deletes the stored database. A volume is not a backup.

To verify persistence, create two synthetic referrals and correct one through
`/docs`. Record their IDs and response bodies. Restart FastAPI, recreate the
container with `docker compose --env-file backend/.env up -d --force-recreate --wait db`,
and retrieve both IDs. The responses should retain the correction, original IDs,
and creation timestamps. Records held by the old in-memory implementation are
not migrated.

Three fictional packets and their expected review outcomes are available in
[`backend/tests/fixtures/referrals`](backend/tests/fixtures/referrals/expected_outcomes.md).
These text files are manual examples, not uploadable API inputs.

## PDF document intake

After updating the backend dependencies, run `alembic upgrade head` from
`backend/` to create the document tables. Existing referrals are retained.
Create a referral first using the manual workflow above, then attach a PDF:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/referrals/{referral_id}/documents` | Upload and parse one PDF |
| GET | `/api/referrals/{referral_id}/documents` | List document metadata in creation order |
| GET | `/api/referrals/{referral_id}/documents/{document_id}` | Retrieve metadata and numbered page text |

In `/docs`, expand the document POST endpoint, select **Try it out**, supply an
existing referral UUID, and choose a synthetic text-based PDF in the `file` field.
The request uses `multipart/form-data`. A successful request returns `201` after
the original file, document metadata, and extracted pages have been saved.
The detail endpoint returns the same response; list responses omit `pages`.

For example, with an existing referral ID and a local synthetic PDF:

```sh
curl --fail-with-body \
  -F 'file=@/absolute/path/to/synthetic-referral.pdf;type=application/pdf' \
  http://127.0.0.1:8000/api/referrals/REFERRAL_UUID/documents
```

The response includes a generated document UUID, referral UUID, display filename,
SHA-256 checksum of the original bytes, byte size, page count, parser version,
UTC creation timestamp, and `parse_status`. Each entry in `pages` has a one-based
`page_number`, extracted `text`, and `text_status`:

```json
{
  "page_number": 1,
  "text": "Patient: Avery Morgan\nDOB: 1974-03-12",
  "text_status": "extracted"
}
```

- `parsed`: every page produced non-whitespace text.
- `partial`: at least one page produced text and at least one did not. Those
  pages retain their numbers and have `text_status: "no_text"`. This can indicate
  a blank page or an image-only page; the parser does not determine which.

These statuses describe text extraction only. A PDF with an image and a small
text header may still omit important information from the extracted text.
Parsing does not populate referral fields, check completeness, or approve a case.
Text order follows the PDF parser and may differ from visual reading order.

| Response | Meaning |
| --- | --- |
| `404` | Referral does not exist, or document does not belong to the supplied referral |
| `413` | Uploaded bytes, page count, or extracted text exceed a configured limit |
| `415` | File content does not begin with a PDF header |
| `422` | Missing file, malformed UUID, empty/corrupt/encrypted PDF, no pages, or no usable text anywhere |

File extensions and client MIME types are advisory; the backend checks the PDF
header and parses the actual content. Blank and image-only PDFs are unsupported
by this text-only pipeline. OCR is a later increment. Repeating an upload creates
a separate document with the same checksum; there is no deduplication yet.

Originals default to `backend/var/documents/`, outside the public web directory
and ignored by Git. Filenames on disk are generated UUIDs, files use private
permissions, and the API never exposes storage paths. Client filenames are
sanitized display metadata. Set `DOCUMENT_STORAGE_DIR` to an absolute path to
override the default. Preserve this directory alongside PostgreSQL: the database
contains metadata and text, while the original PDF lives on disk. There is no
original-file download endpoint yet.

Configuration in `backend/.env`:

```dotenv
DOCUMENT_MAX_BYTES=10485760
DOCUMENT_MAX_PAGES=100
DOCUMENT_MAX_TEXT_CHARS=2000000
```

Processing is synchronous and intended for local synthetic documents. The byte
limit is enforced while copying the multipart file into application storage;
FastAPI may spool the incoming multipart upload before this check. Page and text
limits are application bounds, not hard parser CPU or memory isolation.

Validation and ordinary storage/database failures clean up the request's files
and roll back its database changes. Filesystem moves and database commits cannot
form one atomic transaction. A process crash between these steps can leave an
orphan file, and an indeterminate database commit can require reconciliation.
Automated reconciliation is not implemented.

To verify manually, upload a two-page synthetic PDF, check both page numbers and
their text, restart FastAPI, and retrieve the same document UUID again. An image-only
PDF should return `422`; a mixed PDF should retain empty pages and return `partial`.
Automated tests generate synthetic text, image, blank, encrypted, and corrupt
cases, use temporary file storage and an isolated PostgreSQL database, and also
verify retrieval across two real backend processes.

## Rule-based field extraction

After attaching documents to an existing referral, use FastAPI `/docs` or:

```sh
curl --fail-with-body -X POST \
  http://127.0.0.1:8000/api/referrals/REFERRAL_UUID/extractions
```

Apply the latest migration first (`cd backend` then `alembic upgrade head` in
its virtual environment). `POST` returns `201` with a new immutable extraction
run; `GET /api/referrals/{referral_id}/extractions/{extraction_id}` retrieves it.
An unknown referral or scoped extraction returns `404`; a malformed UUID or
attempt to extract before attaching documents returns `422`.

Each run processes all currently attached documents in stable document/page
order using persisted text, records its source document IDs, extractor version
(`rules/1`) and checklist version (`five-required-fields/1`), and survives backend
restarts. Later uploads do not change old runs. Repeating extraction creates a
new run. Results and source associations are committed in one database transaction.

The five fields are patient name, date of birth, referring organization,
requested specialty, and referral reason. Recognized labels include `Patient`
/ `Patient Name`, `DOB` / `Date of Birth`, `Referring Organization` /
`Referring Clinic`, `Requested Specialty` / `Specialty` / `Requested Service`,
and `Reason` / `Referral Reason`. Labels must occupy individual `Label: value`
lines. Matching ignores label case; values retain case with whitespace normalized.
Only ISO dates and cardiology (including `Cardiology consultation`) are supported.

Results contain field candidates with raw values, normalized values, validation
issues, and exact source quotes with document IDs and one-based page numbers.
Repeated equivalent values combine their evidence. Missing values remain null;
invalid or conflicting fields have no selected value. Checklist findings are
`found`, `missing`, `invalid`, or `conflicting`; invalid candidates take precedence
when a field also has other candidates, all of which remain visible.

`complete` means all five fields were found without conflicting/invalid candidates
and no document had textless pages. Partial PDFs retain a source-coverage warning
and cannot produce `complete: true`. Even `parsed` PDFs can omit image content;
this is a limited text baseline, not approval or proof of packet completeness.
The checklist is an illustrative prototype requirement, not institutional policy.

Manual referral values never fill extraction gaps and extraction does not update
them. Creating a referral still requires the five manually entered fields; draft
or document-first intake, OCR, LLM extraction, and applying suggestions through a
review UI are later increments. The synthetic fixture expectations now also cover
automated extraction in `tests/test_extractions.py`.

## Project layout

```text
backend/
  app/
    api/health.py       # API routes and response models
    api/referrals.py    # Create, list, retrieve, and correct referrals
    api/documents.py    # Upload, list, and inspect PDF documents
    schemas/referral.py # Create/update validation and response model
    schemas/document.py # Document metadata and numbered page responses
    database.py         # Engine and request-scoped sessions
    models/referral.py  # PostgreSQL table mapping
    models/document.py  # Document and document-page table mappings
    repositories/       # Transactional referral storage
    services/           # Document-ingestion orchestration
    document_processing/ # PDF-to-page-text reader
    storage/            # Private local original-file storage
    config.py           # Environment settings
    main.py             # FastAPI application and CORS
  alembic/              # Versioned database migrations
  alembic.ini
  tests/                # API and PostgreSQL integration tests
  pyproject.toml        # Python dependencies and tools
compose.yaml            # PostgreSQL service and persistent volume
frontend/
  src/
    api.ts              # Typed API client
    App.tsx             # Starter page and connection state
    styles.css          # Responsive styles
  vite.config.ts        # Development server and API proxy
```

## Checks

Start PostgreSQL using the Compose command above before running backend tests.
The test suite creates a randomly named `referral_test_*` database, applies real
migrations, isolates each database test, and drops only that temporary database
at teardown. The development database is never cleared. The local Compose role
can create databases. Optionally set `TEST_DATABASE_URL` to a different PostgreSQL
server whose role has `CREATEDB`; the supplied database name is replaced with a
random test database name. Test credentials should be dedicated to development.

```sh
cd backend
source .venv/bin/activate
pytest
ruff check .
```

```sh
cd frontend
npm run lint
npm run build
```

## Deployment configuration

`npm run build` creates `frontend/dist`. Serve that directory with a static web server. Configure that server to proxy `/api` to FastAPI, or set `VITE_API_BASE_URL` to the API's public origin **before building**. Vite's proxy only runs during development.

For a separate frontend origin, set `CORS_ORIGINS` in the backend environment to a JSON array of allowed origins, for example `["https://referrals.example.com"]`. Variables prefixed with `VITE_` are public browser configuration; never put secrets in them.

This is a development prototype with manual referral intake, corrections, and
text-based PDF ingestion. PostgreSQL and local file storage are implemented;
rule-based field extraction is implemented. Authentication and approval workflows
are not.

Framework references: [Vite guide](https://vite.dev/guide/) and [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/).
