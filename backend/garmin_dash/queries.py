"""Shared DB queries used by both the FastAPI server and the JSON exporter."""

from __future__ import annotations

from sqlmodel import Session, select

from .db import Activity, BodyRecord, DailyStat, SleepRecord


def latest_summary(session: Session) -> dict:
    latest_daily = session.exec(
        select(DailyStat).order_by(DailyStat.date.desc())
    ).first()
    latest_sleep = session.exec(
        select(SleepRecord).order_by(SleepRecord.date.desc())
    ).first()
    latest_weight = session.exec(
        select(BodyRecord)
        .where(BodyRecord.weight_kg.is_not(None))
        .order_by(BodyRecord.date.desc())
    ).first()
    latest_vo2 = session.exec(
        select(BodyRecord)
        .where(BodyRecord.vo2max.is_not(None))
        .order_by(BodyRecord.date.desc())
    ).first()
    n_activities = len(session.exec(select(Activity.id)).all())
    return {
        "daily": latest_daily,
        "sleep": latest_sleep,
        "weight": latest_weight,
        "vo2max": latest_vo2,
        "activity_count": n_activities,
    }
