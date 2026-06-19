"use client";

import { useEffect, useRef, useState } from "react";
import { DEFAULT_DATA_URL, STATIC_MODE, LS_KEY } from "@/lib/api";

export function Settings({ onSave }: { onSave: () => void }) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState(DEFAULT_DATA_URL);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"ok" | "err" | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem(LS_KEY);
    if (stored) setUrl(stored);
  }, []);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const save = () => {
    const trimmed = url.trim().replace(/\/$/, "");
    localStorage.setItem(LS_KEY, trimmed);
    setOpen(false);
    onSave();
  };

  const test = async () => {
    setTesting(true);
    setTestResult(null);
    const base = url.trim().replace(/\/$/, "");
    const testUrl = STATIC_MODE ? `${base}/summary.json` : `${base}/api/summary`;
    try {
      const res = await fetch(testUrl, { cache: "no-store" });
      setTestResult(res.ok ? "ok" : "err");
    } catch {
      setTestResult("err");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        title="Data source settings"
        className="flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 text-white/50 hover:text-white sm:h-8 sm:w-8"
      >
        <GearIcon />
      </button>

      {open && (
        <div className="absolute right-0 top-12 z-50 w-[calc(100vw-1.5rem)] max-w-sm rounded-xl border border-white/10 bg-zinc-900 p-4 shadow-xl">
          <p className="mb-1 text-sm font-medium">
            {STATIC_MODE ? "Data folder URL" : "Backend API URL"}
          </p>
          <p className="mb-3 text-xs text-white/40">
            {STATIC_MODE
              ? "URL of your IONOS data folder where the JSON files are hosted (e.g. https://yourdomain.com/garmin-data). Saved in localStorage."
              : "Address of your running FastAPI backend (e.g. a Cloudflare Tunnel or ngrok URL). Saved in localStorage."}
          </p>
          <input
            className="mb-2 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-blue-500"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setTestResult(null);
            }}
            placeholder={STATIC_MODE ? "https://yourdomain.com/garmin-data" : "http://localhost:8000"}
            spellCheck={false}
          />
          <div className="flex items-center gap-2">
            <button
              onClick={test}
              disabled={testing}
              className="rounded-lg border border-white/10 px-3 py-1.5 text-sm hover:bg-white/5 disabled:opacity-50"
            >
              {testing ? "Testing…" : "Test"}
            </button>
            <button
              onClick={save}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium hover:bg-blue-500"
            >
              Save & reload
            </button>
            {testResult === "ok" && (
              <span className="text-xs text-green-400">✓ Connected</span>
            )}
            {testResult === "err" && (
              <span className="text-xs text-red-400">✗ Unreachable</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function GearIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}
