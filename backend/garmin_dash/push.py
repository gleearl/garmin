"""Push cached Garmin data from the local SQLite DB to the Laravel backend.

Reads the same rows the static exporter does and POSTs them to Laravel's
``/api/garmin/ingest`` endpoint (idempotent upserts), instead of writing JSON
files. Used by the GitHub Actions sync so Laravel becomes the live data source.

Run:  uv run python -m garmin_dash.push

Env:
  LARAVEL_INGEST_URL    e.g. https://backend.gleearl.com/api/garmin/ingest
  LARAVEL_INGEST_TOKEN  Sanctum token with the ``garmin:ingest`` ability
  GARMIN_EMAIL          used as ``source_user`` (which Garmin account); optional,
                        defaults to "default" for a single-user dashboard.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from sqlmodel import Session, select

from .db import Activity, BodyRecord, DailyStat, SleepRecord, engine, init_db


def build_payload(source_user: str) -> dict:
    """Build the multi-dataset ingest payload from the SQLite cache.

    Uses the same ``model_dump()`` serialization as the JSON exporter, so the
    shapes match the Laravel ingest contract (activities keyed by Garmin ``id``,
    daily/sleep/body keyed by ``date``).
    """
    init_db()
    with Session(engine) as s:
        daily = s.exec(select(DailyStat).order_by(DailyStat.date)).all()
        sleep = s.exec(select(SleepRecord).order_by(SleepRecord.date)).all()
        activities = s.exec(select(Activity).order_by(Activity.start_time)).all()
        body = s.exec(select(BodyRecord).order_by(BodyRecord.date)).all()

    return {
        "source_user": source_user,
        "daily": [r.model_dump() for r in daily],
        "sleep": [r.model_dump() for r in sleep],
        "activities": [r.model_dump() for r in activities],
        "body": [r.model_dump() for r in body],
    }


def run_push() -> int:
    url = os.environ["LARAVEL_INGEST_URL"]
    token = os.environ["LARAVEL_INGEST_TOKEN"]
    source_user = os.environ.get("GARMIN_EMAIL") or "default"

    payload = build_payload(source_user)
    counts = {k: len(v) for k, v in payload.items() if isinstance(v, list)}
    print(f"Pushing to {url} as source_user={source_user!r}: {counts}")

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            print(f"  -> {resp.status} {resp.read().decode()[:300]}")
    except urllib.error.HTTPError as e:
        print(f"  -> HTTP {e.code}: {e.read().decode()[:300]}")
        return 1
    return 0


def main() -> None:
    sys.exit(run_push())


if __name__ == "__main__":
    main()
