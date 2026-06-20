"""Local MCP server exposing the user's Garmin data to Claude.

Wraps the Laravel backend's read API (/api/garmin/*) as MCP tools, so Claude
(Desktop / Code) can read and reason over the data. Runs over stdio — the Claude
app launches it on demand; nothing is hosted.

Run:  uv run python -m garmin_dash.mcp_server

Env:
  GARMIN_API_URL     Base URL of the Laravel backend (default https://backend.gleearl.com)
  GARMIN_READ_TOKEN  Sanctum token with the garmin:read ability (artisan garmin:token --read)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from mcp.server.fastmcp import FastMCP

API_URL = os.environ.get("GARMIN_API_URL", "https://backend.gleearl.com").rstrip("/")

mcp = FastMCP("garmin-health")


def _get(path: str, params: dict | None = None) -> str:
    """GET {API_URL}{path} with the read token; return the JSON body as text."""
    token = os.environ.get("GARMIN_READ_TOKEN")
    if not token:
        return "Error: GARMIN_READ_TOKEN is not set. Mint one with `artisan garmin:token --read`."

    url = f"{API_URL}{path}"
    if params:
        clean = {k: v for k, v in params.items() if v}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)

    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return "Error: unauthorized (401). The GARMIN_READ_TOKEN is missing/invalid."
        return f"Error: HTTP {e.code} from {path}: {e.read().decode()[:300]}"
    except urllib.error.URLError as e:
        return f"Error: could not reach {API_URL}: {e}"


@mcp.tool()
def summary() -> str:
    """Latest headline health metrics: most recent daily stats, sleep, weight,
    VO2max, and total activity count. Good for a quick 'how am I doing' overview."""
    return _get("/api/garmin/summary")


@mcp.tool()
def daily(from_date: str | None = None, to_date: str | None = None) -> str:
    """Daily health rollups (steps, resting_hr, stress_avg, body_battery_high/low,
    total/active calories, intensity_minutes) per day. Dates are YYYY-MM-DD;
    omit both for the last ~90 days."""
    return _get("/api/garmin/daily", {"from": from_date, "to": to_date})


@mcp.tool()
def sleep(from_date: str | None = None, to_date: str | None = None) -> str:
    """Sleep records per night: total/deep/light/rem/awake seconds and sleep_score.
    Dates are YYYY-MM-DD; omit both for the last ~90 days."""
    return _get("/api/garmin/sleep", {"from": from_date, "to": to_date})


@mcp.tool()
def activities(from_date: str | None = None, to_date: str | None = None) -> str:
    """Workouts/activities: activity_type, start_time, distance_m, duration_s,
    avg_hr, max_hr, calories, avg_speed_mps, elevation_gain_m. Dates are
    YYYY-MM-DD (filter by start date); omit both for the last ~90 days."""
    return _get("/api/garmin/activities", {"from": from_date, "to": to_date})


@mcp.tool()
def body(from_date: str | None = None, to_date: str | None = None) -> str:
    """Body composition & fitness per day: weight_kg, body_fat_pct, bmi, vo2max.
    Dates are YYYY-MM-DD; omit both for the last ~90 days."""
    return _get("/api/garmin/body", {"from": from_date, "to": to_date})


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
