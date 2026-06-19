// Typed fetch helpers for the Garmin dashboard backend.
// Base URL comes from NEXT_PUBLIC_API_URL, defaulting to the local FastAPI dev server.

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface DailyStat {
  date: string;
  steps: number | null;
  resting_hr: number | null;
  stress_avg: number | null;
  body_battery_high: number | null;
  body_battery_low: number | null;
  total_calories: number | null;
  active_calories: number | null;
  intensity_minutes: number | null;
}

export interface SleepRecord {
  date: string;
  total_seconds: number | null;
  deep_seconds: number | null;
  light_seconds: number | null;
  rem_seconds: number | null;
  awake_seconds: number | null;
  sleep_score: number | null;
}

export interface Activity {
  id: number;
  start_time: string | null;
  activity_type: string | null;
  distance_m: number | null;
  duration_s: number | null;
  avg_hr: number | null;
  max_hr: number | null;
  calories: number | null;
  avg_speed_mps: number | null;
  elevation_gain_m: number | null;
}

export interface BodyRecord {
  date: string;
  weight_kg: number | null;
  body_fat_pct: number | null;
  bmi: number | null;
  vo2max: number | null;
}

export interface Summary {
  daily: DailyStat | null;
  sleep: SleepRecord | null;
  weight: BodyRecord | null;
  vo2max: BodyRecord | null;
  activity_count: number;
}

function range(params?: { from?: string; to?: string }) {
  if (!params?.from || !params?.to) return "";
  return `?from=${params.from}&to=${params.to}`;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} -> ${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  summary: () => get<Summary>("/api/summary"),
  daily: (r?: { from?: string; to?: string }) =>
    get<DailyStat[]>(`/api/daily${range(r)}`),
  sleep: (r?: { from?: string; to?: string }) =>
    get<SleepRecord[]>(`/api/sleep${range(r)}`),
  activities: (r?: { from?: string; to?: string }) =>
    get<Activity[]>(`/api/activities${range(r)}`),
  body: (r?: { from?: string; to?: string }) =>
    get<BodyRecord[]>(`/api/body${range(r)}`),
  sync: async (days = 90) => {
    const res = await fetch(`${BASE}/api/sync?days=${days}`, { method: "POST" });
    if (!res.ok) throw new Error(`sync failed: ${res.status}`);
    return res.json();
  },
};
