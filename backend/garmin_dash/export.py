"""Export all cached Garmin data to static JSON files for IONOS hosting.

Run:  uv run python -m garmin_dash.export

Writes to GARMIN_EXPORT_DIR (default: ./export):
  daily.json, sleep.json, activities.json, body.json, summary.json, meta.json

These files are then uploaded to the IONOS web-accessible data folder.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from .db import Activity, BodyRecord, DailyStat, SleepRecord, engine, init_db
from .queries import latest_summary

EXPORT_DIR = os.getenv(
    "GARMIN_EXPORT_DIR",
    str(Path(__file__).resolve().parent.parent / "export"),
)


def _serialize(obj) -> object:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


def run_export() -> None:
    init_db()
    out = Path(EXPORT_DIR)
    out.mkdir(parents=True, exist_ok=True)

    with Session(engine) as s:
        daily = s.exec(select(DailyStat).order_by(DailyStat.date)).all()
        sleep = s.exec(select(SleepRecord).order_by(SleepRecord.date)).all()
        activities = s.exec(
            select(Activity).order_by(Activity.start_time.desc())
        ).all()
        body = s.exec(select(BodyRecord).order_by(BodyRecord.date)).all()
        summary = latest_summary(s)

    def write(name: str, data: object) -> None:
        path = out / name
        with open(path, "w") as f:
            json.dump(data, f)
        print(f"  {path}  ({path.stat().st_size:,} bytes)")

    print(f"Exporting to {out}/")
    write("daily.json", [r.model_dump() for r in daily])
    write("sleep.json", [r.model_dump() for r in sleep])
    write("activities.json", [r.model_dump() for r in activities])
    write("body.json", [r.model_dump() for r in body])
    write(
        "summary.json",
        {k: _serialize(v) for k, v in summary.items()},
    )
    write("meta.json", {"last_updated": datetime.now(timezone.utc).isoformat()})
    print("Export complete.")


def main() -> None:
    run_export()


if __name__ == "__main__":
    main()
