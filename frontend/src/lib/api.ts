// Typed fetch helpers for the Garmin dashboard.
//
// Two modes controlled by build-time env vars:
//
//   NEXT_PUBLIC_DATA_URL (static mode, IONOS)
//     Fetches pre-exported JSON files. Date filtering is done client-side.
//     Set this in the GitHub Actions / IONOS deploy.
//
//   NEXT_PUBLIC_API_URL (live mode, local dev / Oracle VM)
//     Calls the running FastAPI server. Date filtering is server-side.
//     Falls back to http://localhost:8000.
//
// At runtime, localStorage key "garmin_data_url" overrides either default,
// letting the user point the Pages build at any data source via Settings.

export const DEFAULT_DATA_URL: string =
  process.env.NEXT_PUBLIC_DATA_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

export const STATIC_MODE: boolean =
  typeof process.env.NEXT_PUBLIC_DATA_URL === "string" &&
  process.env.NEXT_PUBLIC_DATA_URL.length > 0;

export const LS_KEY = "garmin_data_url";

function getBase(): string {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(LS_KEY);
    if (stored) return stored.replace(/\/$/, "");
  }
  return DEFAULT_DATA_URL;
}

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

export interface Meta {
  last_updated: string; // ISO 8601 UTC
}

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${url} -> ${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

// --- Static mode helpers (IONOS) ---

function filterByDate<T extends { date: string }>(
  rows: T[],
  from?: string,
  to?: string,
): T[] {
  if (!from && !to) return rows;
  return rows.filter(
    (r) => (!from || r.date >= from) && (!to || r.date <= to),
  );
}

function filterActivities(
  rows: Activity[],
  from?: string,
  to?: string,
): Activity[] {
  if (!from && !to) return rows;
  return rows.filter((a) => {
    const d = a.start_time?.slice(0, 10);
    return d && (!from || d >= from) && (!to || d <= to);
  });
}

// --- Live mode helpers (local dev / FastAPI) ---

function liveRange(params?: { from?: string; to?: string }) {
  if (!params?.from || !params?.to) return "";
  return `?from=${params.from}&to=${params.to}`;
}

// --- Unified API surface ---

export const api = {
  summary: (): Promise<Summary> => {
    const base = getBase();
    return STATIC_MODE
      ? get<Summary>(`${base}/summary.json`)
      : get<Summary>(`${base}/api/summary`);
  },

  meta: (): Promise<Meta> => {
    const base = getBase();
    return STATIC_MODE
      ? get<Meta>(`${base}/meta.json`)
      : Promise.resolve({ last_updated: new Date().toISOString() });
  },

  daily: async (r?: { from?: string; to?: string }): Promise<DailyStat[]> => {
    const base = getBase();
    if (STATIC_MODE) {
      const all = await get<DailyStat[]>(`${base}/daily.json`);
      return filterByDate(all, r?.from, r?.to);
    }
    return get<DailyStat[]>(`${base}/api/daily${liveRange(r)}`);
  },

  sleep: async (r?: { from?: string; to?: string }): Promise<SleepRecord[]> => {
    const base = getBase();
    if (STATIC_MODE) {
      const all = await get<SleepRecord[]>(`${base}/sleep.json`);
      return filterByDate(all, r?.from, r?.to);
    }
    return get<SleepRecord[]>(`${base}/api/sleep${liveRange(r)}`);
  },

  activities: async (r?: {
    from?: string;
    to?: string;
  }): Promise<Activity[]> => {
    const base = getBase();
    if (STATIC_MODE) {
      const all = await get<Activity[]>(`${base}/activities.json`);
      return filterActivities(all, r?.from, r?.to);
    }
    return get<Activity[]>(`${base}/api/activities${liveRange(r)}`);
  },

  body: async (r?: { from?: string; to?: string }): Promise<BodyRecord[]> => {
    const base = getBase();
    if (STATIC_MODE) {
      const all = await get<BodyRecord[]>(`${base}/body.json`);
      return filterByDate(all, r?.from, r?.to);
    }
    return get<BodyRecord[]>(`${base}/api/body${liveRange(r)}`);
  },
};
