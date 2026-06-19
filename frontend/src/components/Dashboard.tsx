"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  BodyRecord,
  DailyStat,
  SleepRecord,
  Summary,
  api,
} from "@/lib/api";
import {
  fmtNum,
  metersToKm,
  paceMinPerKm,
  secsToH,
  secsToHours,
  shortDate,
  titleCase,
} from "@/lib/format";
import { StatCard, Panel } from "./Card";
import { AreaTrend, LineTrend, StackedBars } from "./charts";

type Tab = "overview" | "activities" | "sleep" | "daily" | "body";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "activities", label: "Activities" },
  { id: "sleep", label: "Sleep" },
  { id: "daily", label: "Daily Health" },
  { id: "body", label: "Body & Fitness" },
];

const RANGES = [
  { days: 30, label: "30d" },
  { days: 90, label: "90d" },
  { days: 365, label: "1y" },
];

function rangeParams(days: number) {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - (days - 1));
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { from: iso(start), to: iso(end) };
}

export default function Dashboard() {
  const [tab, setTab] = useState<Tab>("overview");
  const [days, setDays] = useState(90);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [daily, setDaily] = useState<DailyStat[]>([]);
  const [sleep, setSleep] = useState<SleepRecord[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [body, setBody] = useState<BodyRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const r = rangeParams(days);
    try {
      const [s, d, sl, a, b] = await Promise.all([
        api.summary(),
        api.daily(r),
        api.sleep(r),
        api.activities(r),
        api.body(r),
      ]);
      setSummary(s);
      setDaily(d);
      setSleep(sl);
      setActivities(a);
      setBody(b);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to reach the API. Is it running?",
      );
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  const onSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      await api.sync(days);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const hasData =
    summary &&
    (summary.daily || daily.length || sleep.length || activities.length);

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Garmin Dashboard</h1>
          <p className="text-sm text-white/40">
            Local cache · {summary?.activity_count ?? 0} activities stored
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex overflow-hidden rounded-lg border border-white/10">
            {RANGES.map((r) => (
              <button
                key={r.days}
                onClick={() => setDays(r.days)}
                className={`px-3 py-1.5 text-sm ${
                  days === r.days
                    ? "bg-white/15 text-white"
                    : "text-white/50 hover:text-white"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
          <button
            onClick={onSync}
            disabled={syncing}
            className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
          >
            {syncing ? "Syncing…" : "Sync now"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="mb-6 flex gap-1 border-b border-white/10">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${
              tab === t.id
                ? "border-blue-500 text-white"
                : "border-transparent text-white/50 hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-white/40">Loading…</p>
      ) : !hasData ? (
        <EmptyState onSync={onSync} syncing={syncing} />
      ) : (
        <>
          {tab === "overview" && (
            <Overview summary={summary!} daily={daily} sleep={sleep} body={body} />
          )}
          {tab === "activities" && <Activities activities={activities} />}
          {tab === "sleep" && <Sleep sleep={sleep} />}
          {tab === "daily" && <Daily daily={daily} />}
          {tab === "body" && <Body body={body} />}
        </>
      )}
    </div>
  );
}

function EmptyState({
  onSync,
  syncing,
}: {
  onSync: () => void;
  syncing: boolean;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-10 text-center">
      <p className="text-lg font-medium">No data yet</p>
      <p className="mx-auto mt-1 max-w-md text-sm text-white/50">
        Make sure you have logged in (
        <code className="text-white/70">uv run python -m garmin_dash.login</code>)
        and then pull your data.
      </p>
      <button
        onClick={onSync}
        disabled={syncing}
        className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
      >
        {syncing ? "Syncing…" : "Sync from Garmin"}
      </button>
    </div>
  );
}

function Overview({
  summary,
  daily,
  sleep,
  body,
}: {
  summary: Summary;
  daily: DailyStat[];
  sleep: SleepRecord[];
  body: BodyRecord[];
}) {
  const stepsData = daily.map((d) => ({ date: d.date, steps: d.steps }));
  const sleepData = sleep.map((s) => ({
    date: s.date,
    hours: secsToHours(s.total_seconds),
  }));
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard
          label="Steps"
          value={fmtNum(summary.daily?.steps)}
          sub={shortDate(summary.daily?.date)}
        />
        <StatCard
          label="Resting HR"
          value={summary.daily?.resting_hr ?? "—"}
          sub="bpm"
        />
        <StatCard
          label="Sleep"
          value={secsToH(summary.sleep?.total_seconds)}
          sub={
            summary.sleep?.sleep_score
              ? `score ${summary.sleep.sleep_score}`
              : shortDate(summary.sleep?.date)
          }
        />
        <StatCard
          label="Weight"
          value={
            summary.weight?.weight_kg
              ? `${fmtNum(summary.weight.weight_kg, 1)} kg`
              : "—"
          }
          sub={shortDate(summary.weight?.date)}
        />
        <StatCard
          label="VO₂ Max"
          value={summary.vo2max?.vo2max ? fmtNum(summary.vo2max.vo2max, 1) : "—"}
          sub={shortDate(summary.vo2max?.date)}
        />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Steps">
          <AreaTrend data={stepsData} dataKey="steps" color="#60a5fa" />
        </Panel>
        <Panel title="Sleep duration (hours)">
          <AreaTrend data={sleepData} dataKey="hours" color="#a78bfa" unit="h" />
        </Panel>
      </div>
    </div>
  );
}

function Activities({ activities }: { activities: Activity[] }) {
  if (!activities.length)
    return <p className="text-white/40">No activities in this range.</p>;
  return (
    <Panel title={`Activities (${activities.length})`}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-white/40">
              <th className="py-2 pr-4 font-medium">Date</th>
              <th className="py-2 pr-4 font-medium">Type</th>
              <th className="py-2 pr-4 font-medium">Distance</th>
              <th className="py-2 pr-4 font-medium">Duration</th>
              <th className="py-2 pr-4 font-medium">Pace</th>
              <th className="py-2 pr-4 font-medium">Avg HR</th>
              <th className="py-2 pr-4 font-medium">Cal</th>
            </tr>
          </thead>
          <tbody>
            {activities.map((a) => (
              <tr key={a.id} className="border-t border-white/5">
                <td className="py-2 pr-4 text-white/70">
                  {a.start_time?.slice(0, 10) ?? "—"}
                </td>
                <td className="py-2 pr-4">{titleCase(a.activity_type)}</td>
                <td className="py-2 pr-4 tabular-nums">
                  {a.distance_m ? `${metersToKm(a.distance_m)} km` : "—"}
                </td>
                <td className="py-2 pr-4 tabular-nums">{secsToH(a.duration_s)}</td>
                <td className="py-2 pr-4 tabular-nums">
                  {paceMinPerKm(a.avg_speed_mps)}
                </td>
                <td className="py-2 pr-4 tabular-nums">{a.avg_hr ?? "—"}</td>
                <td className="py-2 pr-4 tabular-nums">{fmtNum(a.calories)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function Sleep({ sleep }: { sleep: SleepRecord[] }) {
  const data = sleep.map((s) => ({
    date: s.date,
    Deep: secsToHours(s.deep_seconds),
    Light: secsToHours(s.light_seconds),
    REM: secsToHours(s.rem_seconds),
    Awake: secsToHours(s.awake_seconds),
    score: s.sleep_score,
  }));
  return (
    <div className="grid gap-4">
      <Panel title="Sleep stages (hours)">
        <StackedBars
          data={data}
          unit="h"
          series={[
            { key: "Deep", color: "#3b82f6", label: "Deep" },
            { key: "Light", color: "#93c5fd", label: "Light" },
            { key: "REM", color: "#a78bfa", label: "REM" },
            { key: "Awake", color: "#f59e0b", label: "Awake" },
          ]}
        />
      </Panel>
      <Panel title="Sleep score">
        <LineTrend data={data} dataKey="score" color="#a78bfa" />
      </Panel>
    </div>
  );
}

function Daily({ daily }: { daily: DailyStat[] }) {
  const bb = daily.map((d) => ({
    date: d.date,
    high: d.body_battery_high,
    low: d.body_battery_low,
  }));
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Steps">
        <AreaTrend data={daily} dataKey="steps" color="#60a5fa" />
      </Panel>
      <Panel title="Resting heart rate (bpm)">
        <LineTrend data={daily} dataKey="resting_hr" color="#f87171" unit=" bpm" />
      </Panel>
      <Panel title="Average stress">
        <LineTrend data={daily} dataKey="stress_avg" color="#fb923c" />
      </Panel>
      <Panel title="Body Battery (high / low)">
        <LineTrend data={bb} dataKey="high" color="#34d399" />
      </Panel>
    </div>
  );
}

function Body({ body }: { body: BodyRecord[] }) {
  const weight = body.filter((b) => b.weight_kg != null);
  const vo2 = body.filter((b) => b.vo2max != null);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Weight (kg)">
        {weight.length ? (
          <LineTrend data={weight} dataKey="weight_kg" color="#22d3ee" unit=" kg" />
        ) : (
          <p className="text-sm text-white/40">No weight data in range.</p>
        )}
      </Panel>
      <Panel title="VO₂ Max">
        {vo2.length ? (
          <LineTrend data={vo2} dataKey="vo2max" color="#34d399" />
        ) : (
          <p className="text-sm text-white/40">No VO₂ max data in range.</p>
        )}
      </Panel>
      <Panel title="Body fat (%)">
        {body.some((b) => b.body_fat_pct != null) ? (
          <LineTrend data={body} dataKey="body_fat_pct" color="#f472b6" unit="%" />
        ) : (
          <p className="text-sm text-white/40">No body-fat data in range.</p>
        )}
      </Panel>
      <Panel title="BMI">
        {body.some((b) => b.bmi != null) ? (
          <LineTrend data={body} dataKey="bmi" color="#facc15" />
        ) : (
          <p className="text-sm text-white/40">No BMI data in range.</p>
        )}
      </Panel>
    </div>
  );
}
