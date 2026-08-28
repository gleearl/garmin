// Small presentation helpers shared across charts and cards.

export const fmtNum = (n: number | null | undefined, dp = 0) =>
  n == null ? "—" : n.toLocaleString(undefined, { maximumFractionDigits: dp });

export const secsToH = (s: number | null | undefined) =>
  s == null ? "—" : `${Math.floor(s / 3600)}h ${Math.round((s % 3600) / 60)}m`;

export const secsToHours = (s: number | null | undefined) =>
  s == null ? null : +(s / 3600).toFixed(2);

export const metersToKm = (m: number | null | undefined) =>
  m == null ? null : +(m / 1000).toFixed(2);

// Garmin avg speed is m/s; convert to pace (min/km) for run-style activities.
export const paceMinPerKm = (mps: number | null | undefined) => {
  if (!mps) return "—";
  const secPerKm = 1000 / mps;
  const min = Math.floor(secPerKm / 60);
  const sec = Math.round(secPerKm % 60);
  return `${min}:${sec.toString().padStart(2, "0")} /km`;
};

export const shortDate = (d: string | null | undefined) =>
  d == null ? "—" : d.slice(5); // MM-DD

export const titleCase = (s: string | null | undefined) =>
  s == null
    ? "—"
    : s
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());

// Blood-pressure readings are timestamped, not daily — show the day plus time.
export const shortDateTime = (d: string | null | undefined) =>
  d == null ? "—" : d.length > 10 ? `${d.slice(5, 10)} ${d.slice(11, 16)}` : d.slice(5);

/** AHA blood-pressure category for a reading (the higher of the two wins).
 *  ``short`` is for the narrow overview card, where the full label wraps. */
export const bpCategory = (
  systolic: number | null | undefined,
  diastolic: number | null | undefined,
): { label: string; short: string; color: string } | null => {
  if (systolic == null || diastolic == null) return null;
  if (systolic >= 180 || diastolic >= 120)
    return { label: "Hypertensive crisis", short: "Crisis", color: "#ef4444" };
  if (systolic >= 140 || diastolic >= 90)
    return { label: "Stage 2 hypertension", short: "Stage 2", color: "#f87171" };
  if (systolic >= 130 || diastolic >= 80)
    return { label: "Stage 1 hypertension", short: "Stage 1", color: "#fb923c" };
  if (systolic >= 120)
    return { label: "Elevated", short: "Elevated", color: "#facc15" };
  return { label: "Normal", short: "Normal", color: "#34d399" };
};
