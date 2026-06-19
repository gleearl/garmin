// Minimal client-side CSV generation + download (no dependencies).

/** Convert an array of objects to CSV text using an explicit column order
 *  (so headers are present even when there are zero rows). */
export function toCSV<T extends object>(rows: T[], columns: string[]): string {
  const esc = (v: unknown) => {
    if (v == null) return "";
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = columns.join(",");
  const body = rows
    .map((r) => columns.map((c) => esc((r as Record<string, unknown>)[c])).join(","))
    .join("\n");
  return body ? `${header}\n${body}` : header;
}

/** Trigger a browser download of CSV text as a file. */
export function downloadCSV(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
