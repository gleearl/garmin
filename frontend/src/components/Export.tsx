"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { downloadCSV, toCSV } from "@/lib/csv";
import { Panel } from "./Card";

type DatasetKey = "daily" | "sleep" | "activities" | "body";

const COLUMNS: Record<DatasetKey, string[]> = {
  daily: [
    "date", "steps", "resting_hr", "stress_avg", "body_battery_high",
    "body_battery_low", "total_calories", "active_calories", "intensity_minutes",
  ],
  sleep: [
    "date", "total_seconds", "deep_seconds", "light_seconds", "rem_seconds",
    "awake_seconds", "sleep_score",
  ],
  activities: [
    "id", "start_time", "activity_type", "distance_m", "duration_s", "avg_hr",
    "max_hr", "calories", "avg_speed_mps", "elevation_gain_m",
  ],
  body: ["date", "weight_kg", "body_fat_pct", "bmi", "vo2max"],
};

const FETCHERS: Record<
  DatasetKey,
  (r: { from: string; to: string }) => Promise<object[]>
> = {
  daily: api.daily,
  sleep: api.sleep,
  activities: api.activities,
  body: api.body,
};

const DATASET_LABELS: Record<DatasetKey, string> = {
  daily: "Daily health",
  sleep: "Sleep",
  activities: "Activities",
  body: "Body & fitness",
};

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const selectClass =
  "w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-blue-500 sm:w-auto";

export default function Export() {
  const [years, setYears] = useState<number[]>([]);
  const [year, setYear] = useState<string>("all");
  const [month, setMonth] = useState<string>("all");
  const [dataset, setDataset] = useState<DatasetKey | "all">("all");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Discover which years actually have data, for the year dropdown.
  useEffect(() => {
    (async () => {
      try {
        const today = new Date().toISOString().slice(0, 10);
        const rows = await api.daily({ from: "2010-01-01", to: today });
        const ys = Array.from(new Set(rows.map((r) => r.date.slice(0, 4))))
          .map(Number)
          .sort((a, b) => b - a);
        setYears(ys);
      } catch {
        // Backend unreachable — leave year list empty ("All time" still works).
      }
    })();
  }, []);

  const range = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    if (year === "all") return { from: "2010-01-01", to: today };
    if (month === "all") return { from: `${year}-01-01`, to: `${year}-12-31` };
    const m = Number(month); // 1-12
    const lastDay = new Date(Number(year), m, 0).getDate();
    const mm = String(m).padStart(2, "0");
    return {
      from: `${year}-${mm}-01`,
      to: `${year}-${mm}-${String(lastDay).padStart(2, "0")}`,
    };
  }, [year, month]);

  const rangeLabel =
    year === "all"
      ? "all-time"
      : month === "all"
        ? year
        : `${year}-${String(Number(month)).padStart(2, "0")}`;

  async function handleExport() {
    setBusy(true);
    setErr(null);
    setMsg(null);
    const keys: DatasetKey[] =
      dataset === "all" ? ["daily", "sleep", "activities", "body"] : [dataset];
    try {
      let totalRows = 0;
      let files = 0;
      for (const k of keys) {
        const rows = await FETCHERS[k](range);
        totalRows += rows.length;
        files += 1;
        downloadCSV(`garmin_${k}_${rangeLabel}.csv`, toCSV(rows, COLUMNS[k]));
        // Small gap so browsers don't drop rapid sequential downloads.
        await new Promise((res) => setTimeout(res, 200));
      }
      setMsg(`Downloaded ${files} file${files > 1 ? "s" : ""} · ${totalRows} rows · ${rangeLabel}.`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title="Export data to CSV">
      <p className="mb-4 text-sm text-white/50">
        Pick a range and dataset, then download. Files are generated in your
        browser from the current cache.
      </p>

      <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:flex-wrap sm:items-end">
        <label className="flex w-full flex-col gap-1 text-xs text-white/50 sm:w-auto">
          Year
          <select
            className={selectClass}
            value={year}
            onChange={(e) => setYear(e.target.value)}
          >
            <option value="all">All time</option>
            {years.map((y) => (
              <option key={y} value={String(y)}>
                {y}
              </option>
            ))}
          </select>
        </label>

        <label className="flex w-full flex-col gap-1 text-xs text-white/50 sm:w-auto">
          Month
          <select
            className={selectClass}
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            disabled={year === "all"}
          >
            <option value="all">All months</option>
            {MONTHS.map((name, i) => (
              <option key={name} value={String(i + 1)}>
                {name}
              </option>
            ))}
          </select>
        </label>

        <label className="flex w-full flex-col gap-1 text-xs text-white/50 sm:w-auto">
          Dataset
          <select
            className={selectClass}
            value={dataset}
            onChange={(e) => setDataset(e.target.value as DatasetKey | "all")}
          >
            <option value="all">All datasets</option>
            {(Object.keys(DATASET_LABELS) as DatasetKey[]).map((k) => (
              <option key={k} value={k}>
                {DATASET_LABELS[k]}
              </option>
            ))}
          </select>
        </label>

        <button
          onClick={handleExport}
          disabled={busy}
          className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 sm:w-auto"
        >
          {busy ? "Exporting…" : "Download CSV"}
        </button>
      </div>

      {year === "all" && (
        <p className="mt-3 text-xs text-white/30">
          Tip: choose a specific year to enable the month filter.
        </p>
      )}
      {msg && <p className="mt-3 text-sm text-green-400">{msg}</p>}
      {err && <p className="mt-3 text-sm text-red-400">{err}</p>}
    </Panel>
  );
}
