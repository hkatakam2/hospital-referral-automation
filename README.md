# Hospital Referral Automation

FastAPI backend and React + TypeScript frontend, built with Vite.

## Requirements

- Python 3.11 or newer (use `python3.13` below if your default `python3` is older).
- Node.js 22.12+ (or 20.19+) and npm.

## Run locally

Start the backend from the project root:

```sh
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
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

Storage is in memory in a single backend process. Restarting or reloading the
backend removes every referral; multiple worker processes do not share records.
Run one backend worker for this prototype. The frontend still shows the connection
page; use `/docs` for intake. Listing, editing, persistence, and document uploads
are not implemented yet.

Three fictional packets and their expected review outcomes are available in
[`backend/tests/fixtures/referrals`](backend/tests/fixtures/referrals/expected_outcomes.md).
These text files are manual examples, not uploadable API inputs.

## Project layout

```text
backend/
  app/
    api/health.py       # API routes and response models
    api/referrals.py    # Create and retrieve referrals
    schemas/referral.py # Referral request validation and response model
    repositories/      # In-memory referral storage
    config.py           # Environment settings
    main.py             # FastAPI application and CORS
  tests/                # API smoke tests
  pyproject.toml        # Python dependencies and tools
frontend/
  src/
    api.ts              # Typed API client
    App.tsx             # Starter page and connection state
    styles.css          # Responsive styles
  vite.config.ts        # Development server and API proxy
```

## Checks

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

This is a development prototype with manual referral creation and retrieval.
Database storage, authentication, and approval workflows are not implemented yet.

Framework references: [Vite guide](https://vite.dev/guide/) and [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/).
