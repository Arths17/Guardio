"use client";

import { useState } from "react";
import { useGuardioStore } from "@/store/useGuardioStore";
import clsx from "clsx";

const API_BASE = "/api";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "devkey";

async function postApi(path: string, body?: object): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Api-Key": API_KEY,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => String(res.status));
    throw new Error(`${res.status}: ${text}`);
  }
}

const ATTACKS = ["ddos", "malware", "ransomware", "phishing", "botnet", "apt"] as const;

function ThreatBar({ level, status }: { level: number; status: string }) {
  const color =
    status === "CRITICAL" ? "bg-accent-red"
    : status === "HIGH"     ? "bg-accent-orange"
    : status === "ELEVATED" ? "bg-accent-yellow"
    : status === "GUARDED"  ? "bg-accent-cyan"
    : "bg-accent-green";

  const textColor =
    status === "CRITICAL" ? "text-accent-red"
    : status === "HIGH"     ? "text-accent-orange"
    : status === "ELEVATED" ? "text-accent-yellow"
    : status === "GUARDED"  ? "text-accent-cyan"
    : "text-accent-green";

  return (
    <div className="flex items-center gap-2">
      <span className="text-2xs font-mono text-text-muted uppercase tracking-widest">Threat</span>
      <div className="relative w-28 h-1.5 bg-bg-border rounded-full overflow-hidden">
        <div className={clsx("h-full rounded-full transition-all duration-700", color)} style={{ width: `${level}%` }} />
      </div>
      <span className={clsx("text-2xs font-mono font-medium tracking-wider", textColor)}>{status}</span>
      <span className="text-2xs font-mono text-text-muted">{level.toFixed(0)}%</span>
    </div>
  );
}

// Inline toast — appears in the top bar, auto-dismisses
function ErrorToast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="flex items-center gap-2 px-2.5 py-1 bg-accent-red/10 border border-accent-red/30 rounded text-2xs font-mono text-accent-red max-w-xs truncate">
      <span className="flex-1 truncate">{message}</span>
      <button onClick={onDismiss} className="flex-shrink-0 opacity-60 hover:opacity-100">✕</button>
    </div>
  );
}

export default function TopBar() {
  const { connected, running, activeAttack, threatLevel, threatStatus, packetCount, alertCount } =
    useGuardioStore();

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const call = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      const friendly = msg.includes("Failed to fetch") || msg.includes("ECONNREFUSED")
        ? "Cannot reach backend — is it running on port 8000?"
        : msg;
      setError(friendly);
      // Auto-dismiss after 5 s
      setTimeout(() => setError(null), 5000);
    } finally {
      setBusy(false);
    }
  };

  const handleStart  = () => call(() => postApi("/start"));
  const handleStop   = () => call(() => postApi("/stop"));
  const handleAttack = (name: string) => call(() => postApi("/attack", { name }));

  return (
    <header className="flex items-center gap-4 px-4 h-11 bg-bg-surface border-b border-bg-border flex-shrink-0 z-20">
      {/* Wordmark */}
      <div className="flex items-center gap-2 mr-2">
        <svg viewBox="0 0 18 18" fill="none" className="w-4 h-4">
          <path
            d="M9 1L2 4.5v4.5C2 12.5 5.1 15.9 9 17c3.9-1.1 7-4.5 7-8V4.5L9 1z"
            fill="#00C2FF" fillOpacity={0.15} stroke="#00C2FF" strokeWidth={1.2}
          />
          <path d="M6.5 9l2 2 3-3" stroke="#00C2FF" strokeWidth={1.2} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="font-mono text-sm font-medium tracking-widest text-text-primary uppercase">Guardio</span>
        <span className="text-2xs font-mono text-text-muted px-1.5 py-0.5 bg-bg-overlay border border-bg-border rounded">SOC</span>
      </div>

      <div className="w-px h-5 bg-bg-border" />

      {/* Connection status */}
      <div className="flex items-center gap-1.5">
        <span className={clsx("w-1.5 h-1.5 rounded-full", connected ? "bg-accent-green animate-pulse-slow" : "bg-text-muted")} />
        <span className="text-2xs font-mono text-text-muted">{connected ? "LIVE" : "OFFLINE"}</span>
      </div>

      {/* Threat bar */}
      <div className="w-px h-5 bg-bg-border" />
      <ThreatBar level={threatLevel} status={threatStatus} />

      {/* Counters */}
      <div className="w-px h-5 bg-bg-border" />
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1">
          <span className="text-2xs text-text-muted font-mono">PKT</span>
          <span className="text-2xs font-mono text-accent-cyan tabular-nums">{packetCount.toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-2xs text-text-muted font-mono">ALERTS</span>
          <span className={clsx("text-2xs font-mono tabular-nums", alertCount > 0 ? "text-accent-red" : "text-text-muted")}>
            {alertCount}
          </span>
        </div>
      </div>

      <div className="flex-1" />

      {/* Error toast */}
      {error && <ErrorToast message={error} onDismiss={() => setError(null)} />}

      {/* Attack launcher */}
      {running && (
        <div className="flex items-center gap-1">
          <span className="text-2xs font-mono text-text-muted mr-1">LAUNCH</span>
          {ATTACKS.map((atk) => (
            <button
              key={atk}
              onClick={() => handleAttack(atk)}
              disabled={!!activeAttack || busy}
              className={clsx(
                "px-2 py-0.5 text-2xs font-mono rounded border transition-colors",
                activeAttack === atk
                  ? "border-accent-red text-accent-red bg-accent-red/10"
                  : "border-bg-border text-text-muted hover:border-accent-orange hover:text-accent-orange disabled:opacity-40 disabled:cursor-not-allowed"
              )}
            >
              {atk.toUpperCase()}
            </button>
          ))}
        </div>
      )}

      <div className="w-px h-5 bg-bg-border" />

      {/* Sim controls */}
      {!running ? (
        <button
          onClick={handleStart}
          disabled={busy || !connected}
          className={clsx(
            "flex items-center gap-1.5 px-3 py-1 text-2xs font-mono font-medium rounded border transition-colors",
            busy
              ? "border-text-muted text-text-muted cursor-wait"
              : !connected
              ? "border-bg-border text-text-dim cursor-not-allowed"
              : "border-accent-green/40 text-accent-green hover:bg-accent-green/10"
          )}
          title={!connected ? "Backend offline — start uvicorn first" : undefined}
        >
          <span className={clsx("w-1.5 h-1.5 rounded-full", busy ? "bg-text-muted animate-pulse" : !connected ? "bg-text-dim" : "bg-accent-green")} />
          {busy ? "STARTING…" : "START SIM"}
        </button>
      ) : (
        <button
          onClick={handleStop}
          disabled={busy}
          className={clsx(
            "flex items-center gap-1.5 px-3 py-1 text-2xs font-mono font-medium rounded border transition-colors",
            busy ? "border-text-muted text-text-muted cursor-wait" : "border-accent-red/40 text-accent-red hover:bg-accent-red/10"
          )}
        >
          <span className={clsx("w-1.5 h-1.5 rounded-full bg-accent-red", !busy && "animate-pulse")} />
          {busy ? "STOPPING…" : "STOP SIM"}
        </button>
      )}
    </header>
  );
}
