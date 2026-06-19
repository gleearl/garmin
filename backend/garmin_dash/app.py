"""FastAPI server exposing the cached Garmin data to the Next.js frontend.

Run:  uv run uvicorn garmin_dash.app:app --reload

All read endpoints serve from the SQLite cache (fast, offline-capable).
``POST /api/sync`` triggers a fresh pull from Garmin.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .db import Activity, BodyRecord, DailyStat, SleepRecord, engine, init_db
from .queries import latest_summary
from .sync import run_sync

app = FastAPI(title="Garmin Dashboard API")

# Allowed browser origins. Defaults cover local dev plus the GitHub Pages site;
# override with the CORS_ORIGINS env var (comma-separated) if your Pages URL differs.
_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://gleearl.github.io",
]
_origins = os.getenv("CORS_ORIGINS")
allow_origins = (
    [o.strip() for o in _origins.split(",") if o.strip()]
    if _origins
    else _DEFAULT_ORIGINS
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _default_range(days: int = 90) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


@app.get("/api/daily")
def daily(
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
):
    d0, d1 = (from_, to) if from_ and to else _default_range()
    with Session(engine) as s:
        rows = s.exec(
            select(DailyStat)
            .where(DailyStat.date >= d0, DailyStat.date <= d1)
            .order_by(DailyStat.date)
        ).all()
    return rows


@app.get("/api/sleep")
def sleep(
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
):
    d0, d1 = (from_, to) if from_ and to else _default_range()
    with Session(engine) as s:
        rows = s.exec(
            select(SleepRecord)
            .where(SleepRecord.date >= d0, SleepRecord.date <= d1)
            .order_by(SleepRecord.date)
        ).all()
    return rows


@app.get("/api/activities")
def activities(
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
):
    d0, d1 = (from_, to) if from_ and to else _default_range()
    with Session(engine) as s:
        rows = s.exec(
            select(Activity)
            .where(Activity.start_time >= d0, Activity.start_time <= d1 + " 99")
            .order_by(Activity.start_time.desc())
        ).all()
    return rows


@app.get("/api/body")
def body(
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
):
    d0, d1 = (from_, to) if from_ and to else _default_range()
    with Session(engine) as s:
        rows = s.exec(
            select(BodyRecord)
            .where(BodyRecord.date >= d0, BodyRecord.date <= d1)
            .order_by(BodyRecord.date)
        ).all()
    return rows


@app.get("/api/summary")
def summary():
    """Latest-known value for each headline metric, for the overview cards."""
    with Session(engine) as s:
        return latest_summary(s)


@app.post("/api/sync")
def sync_now(days: int = 90):
    return run_sync(days)
