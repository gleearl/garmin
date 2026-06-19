"""Fetch data from Garmin Connect and upsert it into the SQLite cache.

CLI:   uv run python -m garmin_dash.sync --days 90
Also called by the FastAPI ``POST /api/sync`` endpoint.

Every fetch is wrapped defensively: Garmin's JSON shapes vary by account and
device, and a missing field for one day should never abort the whole sync.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta

from sqlmodel import Session

from .client import get_client
from .db import Activity, BodyRecord, DailyStat, SleepRecord, engine, init_db


def _g(d, *keys, default=None):
    """Safe nested getter: _g(d, 'a', 'b') -> d['a']['b'] or default."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _upsert(session: Session, obj) -> None:
    session.merge(obj)


def sync_daily(client, session: Session, day: str) -> None:
    try:
        s = client.get_stats(day) or {}
    except Exception as err:  # noqa: BLE001
        print(f"  [daily {day}] skipped: {err}")
        return
    _upsert(
        session,
        DailyStat(
            date=day,
            steps=s.get("totalSteps"),
            resting_hr=s.get("restingHeartRate"),
            stress_avg=s.get("averageStressLevel"),
            body_battery_high=s.get("bodyBatteryHighestValue"),
            body_battery_low=s.get("bodyBatteryLowestValue"),
            total_calories=s.get("totalKilocalories"),
            active_calories=s.get("activeKilocalories"),
            intensity_minutes=(s.get("moderateIntensityMinutes") or 0)
            + (s.get("vigorousIntensityMinutes") or 0),
        ),
    )


def sync_sleep(client, session: Session, day: str) -> None:
    try:
        s = client.get_sleep_data(day) or {}
    except Exception as err:  # noqa: BLE001
        print(f"  [sleep {day}] skipped: {err}")
        return
    dto = s.get("dailySleepDTO") or {}
    total = dto.get("sleepTimeSeconds")
    if not total:
        return  # no sleep recorded that night
    _upsert(
        session,
        SleepRecord(
            date=day,
            total_seconds=total,
            deep_seconds=dto.get("deepSleepSeconds"),
            light_seconds=dto.get("lightSleepSeconds"),
            rem_seconds=dto.get("remSleepSeconds"),
            awake_seconds=dto.get("awakeSleepSeconds"),
            sleep_score=_g(dto, "sleepScores", "overall", "value"),
        ),
    )


def sync_body(client, session: Session, start: str, end: str) -> None:
    try:
        b = client.get_body_composition(start, end) or {}
    except Exception as err:  # noqa: BLE001
        print(f"  [body] skipped: {err}")
        return
    for entry in b.get("dateWeightList") or []:
        cal = entry.get("calendarDate")
        if not cal:
            continue
        weight_g = entry.get("weight")
        _upsert(
            session,
            BodyRecord(
                date=cal,
                weight_kg=(weight_g / 1000.0) if weight_g else None,
                body_fat_pct=entry.get("bodyFat"),
                bmi=entry.get("bmi"),
            ),
        )


def sync_vo2max(client, session: Session, day: str) -> None:
    try:
        m = client.get_max_metrics(day)
    except Exception as err:  # noqa: BLE001
        print(f"  [vo2max {day}] skipped: {err}")
        return
    if not m:
        return
    record = m[0] if isinstance(m, list) else m
    vo2 = _g(record, "generic", "vo2MaxPreciseValue") or _g(
        record, "generic", "vo2MaxValue"
    )
    if vo2 is None:
        return
    # Merge into the existing BodyRecord for the day without clobbering weight.
    existing = session.get(BodyRecord, day)
    if existing:
        existing.vo2max = vo2
        session.add(existing)
    else:
        _upsert(session, BodyRecord(date=day, vo2max=vo2))


def sync_activities(client, session: Session, start: str, end: str) -> None:
    try:
        acts = client.get_activities_by_date(start, end) or []
    except Exception as err:  # noqa: BLE001
        print(f"  [activities] skipped: {err}")
        return
    for a in acts:
        aid = a.get("activityId")
        if aid is None:
            continue
        _upsert(
            session,
            Activity(
                id=aid,
                start_time=a.get("startTimeLocal"),
                activity_type=_g(a, "activityType", "typeKey"),
                distance_m=a.get("distance"),
                duration_s=a.get("duration"),
                avg_hr=int(a["averageHR"]) if a.get("averageHR") else None,
                max_hr=int(a["maxHR"]) if a.get("maxHR") else None,
                calories=int(a["calories"]) if a.get("calories") else None,
                avg_speed_mps=a.get("averageSpeed"),
                elevation_gain_m=a.get("elevationGain"),
            ),
        )


def run_sync(days: int = 90) -> dict:
    """Sync the last ``days`` days into SQLite. Returns a small summary."""
    init_db()
    client = get_client()

    end = date.today()
    start = end - timedelta(days=days - 1)
    start_s, end_s = start.isoformat(), end.isoformat()
    print(f"Syncing {start_s} .. {end_s} ({days} days)")

    with Session(engine) as session:
        # Per-day endpoints.
        d = start
        while d <= end:
            day = d.isoformat()
            sync_daily(client, session, day)
            sync_sleep(client, session, day)
            sync_vo2max(client, session, day)
            d += timedelta(days=1)
        # Range endpoints.
        sync_body(client, session, start_s, end_s)
        sync_activities(client, session, start_s, end_s)
        session.commit()

    print("Sync complete.")
    return {"from": start_s, "to": end_s, "days": days}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Garmin data into SQLite.")
    parser.add_argument("--days", type=int, default=90, help="days of history")
    args = parser.parse_args()
    run_sync(args.days)


if __name__ == "__main__":
    main()
