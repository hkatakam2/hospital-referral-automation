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
inspection, and corrections. Document uploads are not implemented yet.

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

## Project layout

```text
backend/
  app/
    api/health.py       # API routes and response models
    api/referrals.py    # Create, list, retrieve, and correct referrals
    schemas/referral.py # Create/update validation and response model
    database.py         # Engine and request-scoped sessions
    models/referral.py  # PostgreSQL table mapping
    repositories/       # Transactional referral storage
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

This is a development prototype with manual referral intake and corrections.
PostgreSQL storage is implemented; authentication and approval workflows are not.

Framework references: [Vite guide](https://vite.dev/guide/) and [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/).
