"use client";

import { useGuardioStore } from "@/store/useGuardioStore";
import clsx from "clsx";

const LEVEL_COLOR: Record<string, string> = {
  critical: "#FF6B6B",
  high:     "#FF9500",
  medium:   "#FFCC66",
};

const LEVEL_TAG: Record<string, string> = {
  critical: "CRIT",
  high:     "HIGH",
  medium:   "MED ",
};

function alertTime(iso: string): string {
  try {
    return new Date(iso).toTimeString().slice(0, 8);
  } catch {
    return "——:——:——";
  }
}

export default function AlertFeed() {
  const alerts = useGuardioStore((s) => s.alerts);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header — minimal, not a card title */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-bg-border flex-shrink-0">
        <span className="text-2xs font-mono text-text-dim uppercase tracking-widest flex-1">
          IDS DETECTIONS
        </span>
        <span
          className={clsx(
            "text-2xs font-mono tabular-nums px-1.5 py-0.5 rounded",
            alerts.length > 0 ? "bg-accent-red/15 text-accent-red" : "text-text-dim"
          )}
        >
          {alerts.length}
        </span>
      </div>

      {/* Log stream — dense, terminal-style rows */}
      <div className="flex-1 overflow-y-auto">
        {alerts.length === 0 ? (
          <div className="flex items-center justify-center h-16 text-2xs font-mono text-text-dim">
            — no detections —
          </div>
        ) : (
          alerts.map((a) => {
            const color = LEVEL_COLOR[a.level] ?? LEVEL_COLOR.medium;
            const tag = LEVEL_TAG[a.level] ?? "MED ";
            return (
              <div
                key={a.alert_id}
                className="flex items-start gap-2 px-3 py-1.5 border-b border-bg-border/40 hover:bg-bg-surface/40 transition-colors animate-fade-in"
                style={{ borderLeft: `2px solid ${color}44` }}
              >
                {/* Timestamp */}
                <span className="text-2xs font-mono text-text-dim tabular-nums flex-shrink-0 mt-px">
                  {alertTime(a.ts)}
                </span>

                {/* Severity tag */}
                <span
                  className="text-2xs font-mono font-bold flex-shrink-0 mt-px w-8"
                  style={{ color }}
                >
                  {tag}
                </span>

                {/* Alert body */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="text-2xs font-mono px-1 py-px bg-bg-border rounded text-text-muted flex-shrink-0">
                      {a.protocol}
                    </span>
                    <span className="text-2xs font-mono text-text-secondary truncate">{a.reason}</span>
                  </div>
                  <div className="text-2xs font-mono text-text-dim mt-0.5 truncate tabular-nums">
                    {a.src} → {a.dst}
                  </div>
                </div>

                {/* Score */}
                <span
                  className="text-2xs font-mono tabular-nums flex-shrink-0 mt-px"
                  style={{ color: `${color}bb` }}
                >
                  {a.score.toFixed(2)}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
