"""SQLite cache schema and engine.

Each metric group gets its own table. Daily tables are keyed by ISO date so a
re-sync simply upserts the same primary key. Activities are keyed by Garmin's
own activity id.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlmodel import Field, SQLModel, create_engine

DB_PATH = os.getenv(
    "GARMIN_DB",
    str(Path(__file__).resolve().parent.parent / "garmin.db"),
)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


class DailyStat(SQLModel, table=True):
    """Daily health rollup (steps, resting HR, stress, Body Battery, etc.)."""

    date: str = Field(primary_key=True)  # YYYY-MM-DD
    steps: int | None = None
    resting_hr: int | None = None
    stress_avg: int | None = None
    body_battery_high: int | None = None
    body_battery_low: int | None = None
    total_calories: int | None = None
    active_calories: int | None = None
    intensity_minutes: int | None = None


class SleepRecord(SQLModel, table=True):
    """One night of sleep, keyed by the calendar date it belongs to."""

    date: str = Field(primary_key=True)  # YYYY-MM-DD
    total_seconds: int | None = None
    deep_seconds: int | None = None
    light_seconds: int | None = None
    rem_seconds: int | None = None
    awake_seconds: int | None = None
    sleep_score: int | None = None


class Activity(SQLModel, table=True):
    """A single workout/activity, keyed by Garmin's activity id."""

    id: int = Field(primary_key=True)
    start_time: str | None = None
    activity_type: str | None = None
    distance_m: float | None = None
    duration_s: float | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    calories: int | None = None
    avg_speed_mps: float | None = None
    elevation_gain_m: float | None = None


class BodyRecord(SQLModel, table=True):
    """Body composition + fitness metrics for a date."""

    date: str = Field(primary_key=True)  # YYYY-MM-DD
    weight_kg: float | None = None
    body_fat_pct: float | None = None
    bmi: float | None = None
    vo2max: float | None = None


def init_db() -> None:
    """Create all tables if they do not yet exist."""
    SQLModel.metadata.create_all(engine)
