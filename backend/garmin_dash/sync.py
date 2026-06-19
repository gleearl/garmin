"""Fetch data from Garmin Connect and upsert it into the SQLite cache.

CLI:
    uv run python -m garmin_dash.sync --days 90              # recent window
    uv run python -m garmin_dash.sync --all                  # full history backfill
    uv run python -m garmin_dash.sync --start 2018-01-01     # explicit range

Also called by the FastAPI ``POST /api/sync`` endpoint.

Every per-day fetch is wrapped defensively: Garmin's JSON shapes vary by account
and device, and a missing field for one day should never abort the whole sync.
Genuine rate-limiting (HTTP 429), however, is handled specially: we back off and
retry, and if Garmin keeps refusing we stop *cleanly* with progress saved, rather
than punching holes in the data. Re-run with ``--skip-existing`` to resume.
"""

from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

from garminconnect import GarminConnectTooManyRequestsError
from sqlmodel import Session

from .client import get_client
from .db import Activity, BodyRecord, DailyStat, SleepRecord, engine, init_db


class RateLimited(Exception):
    """Raised to halt a backfill gracefully when Garmin keeps returning 429."""


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


def _fetch(label: str, method, *args, retries: int = 4, base_wait: float = 5.0):
    """Call a Garmin client method with 429-aware retry/backoff.

    - On success: returns the result.
    - On persistent rate-limiting: raises ``RateLimited`` (stops the backfill so
      progress already committed is kept and can be resumed).
    - On any other error: logs and returns ``None`` so one bad day is skipped
      without aborting the run.
    """
    for attempt in range(1, retries + 1):
        try:
            return method(*args)
        except GarminConnectTooManyRequestsError:
            if attempt == retries:
                raise RateLimited(label)
            wait = base_wait * (2 ** (attempt - 1))
            print(f"  rate-limited at {label}; backing off {wait:.0f}s "
                  f"(attempt {attempt}/{retries})")
            time.sleep(wait)
        except Exception as err:  # noqa: BLE001
            # Some library versions surface a 429 as a generic error string.
            if "429" in str(err):
                if attempt == retries:
                    raise RateLimited(label)
                wait = base_wait * (2 ** (attempt - 1))
                print(f"  rate-limited at {label}; backing off {wait:.0f}s "
                      f"(attempt {attempt}/{retries})")
                time.sleep(wait)
                continue
            print(f"  [{label}] skipped: {err}")
            return None
    return None


def _upsert(session: Session, obj) -> None:
    session.merge(obj)


def sync_daily(client, session: Session, day: str) -> None:
    s = _fetch(f"daily {day}", client.get_stats, day)
    if s is None:
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
    s = _fetch(f"sleep {day}", client.get_sleep_data, day)
    if s is None:
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
    b = _fetch("body", client.get_body_composition, start, end)
    if b is None:
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
    m = _fetch(f"vo2max {day}", client.get_max_metrics, day)
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
    acts = _fetch("activities", client.get_activities_by_date, start, end)
    if not acts:
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


def run_sync(
    days: int = 90,
    start: str | None = None,
    end: str | None = None,
    delay: float = 0.0,
    skip_existing: bool = False,
) -> dict:
    """Sync a date range into SQLite and return a summary.

    The range is ``[start, end]`` when both are given, otherwise the last
    ``days`` days ending today.

    - ``delay``: seconds to pause between days (throttle big backfills).
    - ``skip_existing``: skip days that already have a DailyStat row — makes
      re-runs cheap and lets an interrupted backfill resume where it stopped.

    Progress is committed per day, so a graceful stop (rate-limit) or crash
    never loses already-fetched days.
    """
    init_db()
    client = get_client()

    end_d = date.fromisoformat(end) if end else date.today()
    start_d = date.fromisoformat(start) if start else end_d - timedelta(days=days - 1)
    start_s, end_s = start_d.isoformat(), end_d.isoformat()
    total_days = (end_d - start_d).days + 1
    print(f"Syncing {start_s} .. {end_s} ({total_days} days)"
          + (f", delay={delay}s" if delay else "")
          + (", skip-existing" if skip_existing else ""))

    processed = skipped = 0
    stopped_at: str | None = None

    with Session(engine) as session:
        d = start_d
        try:
            while d <= end_d:
                day = d.isoformat()
                if skip_existing and session.get(DailyStat, day) is not None:
                    skipped += 1
                    d += timedelta(days=1)
                    continue
                sync_daily(client, session, day)
                sync_sleep(client, session, day)
                sync_vo2max(client, session, day)
                session.commit()  # incremental progress
                processed += 1
                if processed % 30 == 0:
                    print(f"  …{day} ({processed} fetched, {skipped} skipped)")
                if delay:
                    time.sleep(delay)
                d += timedelta(days=1)
            # Range endpoints (single calls; cheap relative to the per-day loop).
            sync_body(client, session, start_s, end_s)
            sync_activities(client, session, start_s, end_s)
            session.commit()
        except RateLimited as rl:
            session.commit()
            stopped_at = d.isoformat()
            print(f"\nStopped early — Garmin rate-limited at '{rl}'. "
                  f"Progress saved up to {stopped_at}.\n"
                  f"Wait ~30-60 min, then resume with:\n"
                  f"  uv run python -m garmin_dash.sync "
                  f"--start {start_s} --end {end_s} --skip-existing --delay 2")

    status = "rate-limited" if stopped_at else "complete"
    print(f"Sync {status}. fetched={processed} skipped={skipped}")
    return {
        "from": start_s,
        "to": end_s,
        "days": total_days,
        "fetched": processed,
        "skipped": skipped,
        "status": status,
        "stopped_at": stopped_at,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Garmin data into SQLite.")
    parser.add_argument("--days", type=int, default=90,
                        help="days of history ending today (default 90)")
    parser.add_argument("--start", help="start date YYYY-MM-DD (overrides --days)")
    parser.add_argument("--end", help="end date YYYY-MM-DD (default today)")
    parser.add_argument("--all", action="store_true",
                        help="full history backfill (sets a very old start, "
                             "throttled + resumable)")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="seconds to pause between days (e.g. 2 for backfills)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="skip days already cached (resume / cheap re-run)")
    args = parser.parse_args()

    start = args.start
    delay = args.delay
    skip_existing = args.skip_existing
    if args.all:
        # Garmin Connect launched in 2007; this covers any real account.
        start = start or "2008-01-01"
        skip_existing = True
        if not delay:
            delay = 2.0

    run_sync(
        days=args.days,
        start=start,
        end=args.end,
        delay=delay,
        skip_existing=skip_existing,
    )


if __name__ == "__main__":
    main()
