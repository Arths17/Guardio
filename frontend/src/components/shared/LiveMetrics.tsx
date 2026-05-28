"use client";

import { useGuardioStore } from "@/store/useGuardioStore";

function Stat({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: string | number;
  unit?: string;
  color?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-2xs font-mono text-text-muted uppercase tracking-widest">{label}</span>
      <div className="flex items-baseline gap-1">
        <span className={`text-sm font-mono font-medium tabular-nums ${color ?? "text-text-primary"}`}>
          {value}
        </span>
        {unit && <span className="text-2xs font-mono text-text-dim">{unit}</span>}
      </div>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)}GB`;
}

export default function LiveMetrics() {
  const {
    threatLevel,
    threatStatus,
    packetCount,
    alertCount,
    droppedCount,
    bytesTransferred,
    activeAttack,
    running,
    nodes,
  } = useGuardioStore();

  const compromisedCount = Object.values(nodes).filter(
    (n) => n.state === "compromised" || n.state === "encrypted"
  ).length;

  const threatColor =
    threatStatus === "CRITICAL"
      ? "text-accent-red"
      : threatStatus === "HIGH"
      ? "text-accent-orange"
      : threatStatus === "ELEVATED"
      ? "text-accent-yellow"
      : "text-accent-green";

  return (
    <div className="border-b border-bg-border px-3 py-3 flex-shrink-0">
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-2xs font-mono font-medium text-text-secondary uppercase tracking-widest">
          Live Metrics
        </span>
        <div className="flex items-center gap-1">
          <span
            className={`w-1.5 h-1.5 rounded-full ${running ? "bg-accent-green animate-pulse-slow" : "bg-text-dim"}`}
          />
          <span className="text-2xs font-mono text-text-dim">{running ? "SIM ACTIVE" : "IDLE"}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
        <Stat label="Threat" value={threatStatus} color={threatColor} />
        <Stat label="Level" value={`${threatLevel.toFixed(0)}%`} color={threatColor} />
        <Stat label="Packets" value={packetCount.toLocaleString()} color="text-accent-cyan" />
        <Stat label="Alerts" value={alertCount} color={alertCount > 0 ? "text-accent-red" : "text-text-muted"} />
        <Stat label="Dropped" value={droppedCount} color={droppedCount > 0 ? "text-accent-yellow" : "text-text-muted"} />
        <Stat label="Compromised" value={compromisedCount} color={compromisedCount > 0 ? "text-accent-red" : "text-text-muted"} />
      </div>

      {activeAttack && (
        <div className="mt-2.5 px-2 py-1.5 bg-accent-red/5 border border-accent-red/20 rounded flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-red animate-pulse flex-shrink-0" />
          <span className="text-2xs font-mono text-accent-red uppercase">{activeAttack} in progress</span>
        </div>
      )}

      <div className="mt-2 pt-2 border-t border-bg-border flex items-center justify-between">
        <span className="text-2xs font-mono text-text-muted">Data transferred</span>
        <span className="text-2xs font-mono text-text-secondary tabular-nums">{formatBytes(bytesTransferred)}</span>
      </div>
    </div>
  );
}
