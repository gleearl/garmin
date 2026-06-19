# Garmin Dashboard

A local dashboard for your personal Garmin Connect data — activities, sleep, daily
health (steps, resting HR, stress, Body Battery), and body/fitness (weight, VO₂ max).

- **Backend** (`backend/`): Python + FastAPI. Logs into Garmin Connect via the unofficial
  [`garminconnect`](https://github.com/cyberjunky/python-garminconnect) library, caches your
  data in SQLite, and serves it over a small JSON API.
- **Frontend** (`frontend/`): Next.js + TypeScript + Tailwind + Recharts. Reads from the
  backend and renders charts.

The dashboard reads from the SQLite cache, so it's fast and works offline. A **Sync now**
button (or the CLI) re-pulls fresh data from Garmin.

> ⚠️ `garminconnect` is **unofficial** — it logs in as the Garmin Connect mobile app would.
> Keep everything local; never commit `garmin.db` or `.env`. Garmin can change their
> endpoints, so occasional maintenance may be needed.

## Prerequisites

- **Node.js** 20+ (for the frontend) — already present.
- **[uv](https://docs.astral.sh/uv/)** for the Python backend. It downloads its own
  Python 3.12, so you don't need to install Python yourself:

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

## Backend

```bash
cd backend
uv sync                                       # create the venv + install deps

# One-time: log in (handles MFA). Prompts for email/password/OTP, or read them
# from a .env file (copy backend/.env.example -> backend/.env).
uv run python -m garmin_dash.login

# Pull your data into the SQLite cache (default 90 days).
uv run python -m garmin_dash.sync --days 90

# Start the API on http://localhost:8000
uv run uvicorn garmin_dash.app:app --reload
```

API endpoints: `GET /api/{summary,daily,sleep,activities,body}` and `POST /api/sync?days=N`.
All accept optional `?from=YYYY-MM-DD&to=YYYY-MM-DD`.

## Frontend

```bash
cd frontend
npm install
npm run dev                                   # http://localhost:3000
```

Open <http://localhost:3000>. If the cache is empty, click **Sync from Garmin** (this calls
`POST /api/sync` on the backend). Use the 30d / 90d / 1y selector and the tabs to explore.

Set `NEXT_PUBLIC_API_URL` (see `frontend/.env.example`) if the backend isn't on
`localhost:8000`.

## Project layout

```
backend/
  garmin_dash/
    login.py     one-time interactive login (MFA), persists tokens
    client.py    garminconnect wrapper + token store handling
    db.py        SQLite schema (SQLModel): DailyStat, SleepRecord, Activity, BodyRecord
    sync.py      fetch a date range from Garmin -> upsert into SQLite (CLI + used by API)
    app.py       FastAPI endpoints reading from the cache
frontend/
  src/lib/api.ts        typed fetch helpers + response types
  src/lib/format.ts     presentation helpers (units, dates, pace)
  src/components/        Dashboard, Card, charts (Recharts)
  src/app/page.tsx       renders <Dashboard/>
```

## Notes

- Tokens are stored at `~/.garminconnect` and auto-refresh; you only run `login` again if
  the session expires.
- The SQLite cache lives at `backend/garmin.db` (gitignored). Delete it to start fresh.
