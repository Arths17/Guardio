"use client";

import { useGuardioStore } from "@/store/useGuardioStore";
import { formatDistanceToNowStrict } from "date-fns";
import clsx from "clsx";

const LEVEL_STYLES = {
  critical: { dot: "bg-accent-red", text: "text-accent-red", bg: "bg-accent-red/5 border-accent-red/20" },
  high:     { dot: "bg-accent-orange", text: "text-accent-orange", bg: "bg-accent-orange/5 border-accent-orange/20" },
  medium:   { dot: "bg-accent-yellow", text: "text-accent-yellow", bg: "bg-accent-yellow/5 border-accent-yellow/20" },
};

export default function AlertFeed() {
  const alerts = useGuardioStore((s) => s.alerts);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-bg-border flex-shrink-0">
        <span className="text-2xs font-mono font-medium text-text-secondary uppercase tracking-widest">
          IDS Alerts
        </span>
        <span className="text-2xs font-mono text-accent-red tabular-nums">{alerts.length}</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {alerts.length === 0 ? (
          <div className="flex items-center justify-center h-20 text-2xs font-mono text-text-dim">
            NO ALERTS
          </div>
        ) : (
          <div className="divide-y divide-bg-border">
            {alerts.map((a) => {
              const s = LEVEL_STYLES[a.level] ?? LEVEL_STYLES.medium;
              return (
                <div
                  key={a.alert_id}
                  className={clsx(
                    "px-3 py-2 border-l-2 animate-fade-in",
                    a.level === "critical"
                      ? "border-l-accent-red"
                      : a.level === "high"
                      ? "border-l-accent-orange"
                      : "border-l-accent-yellow"
                  )}
                >
                  <div className="flex items-start justify-between gap-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className={clsx("w-1.5 h-1.5 rounded-full flex-shrink-0", s.dot)} />
                      <span className={clsx("text-2xs font-mono font-medium flex-shrink-0", s.text)}>
                        {a.level.toUpperCase()}
                      </span>
                    </div>
                    <span className="text-2xs font-mono text-text-dim flex-shrink-0 tabular-nums">
                      {(() => {
                        try {
                          return formatDistanceToNowStrict(new Date(a.ts), { addSuffix: true });
                        } catch {
                          return "";
                        }
                      })()}
                    </span>
                  </div>
                  <div className="text-2xs text-text-secondary mt-0.5 leading-tight truncate">
                    {a.reason}
                  </div>
                  <div className="flex items-center gap-1 mt-0.5">
                    <span className="text-2xs font-mono text-text-dim truncate">{a.src}</span>
                    <span className="text-2xs text-text-dim">→</span>
                    <span className="text-2xs font-mono text-text-dim truncate">{a.dst}</span>
                  </div>
                  <div className="flex items-center gap-1 mt-0.5">
                    <span className="text-2xs font-mono px-1 py-0.5 bg-bg-border rounded text-text-muted">
                      {a.protocol}
                    </span>
                    <span className="text-2xs font-mono text-text-dim">score {a.score.toFixed(2)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
