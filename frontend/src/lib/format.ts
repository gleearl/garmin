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
