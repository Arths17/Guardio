"use client";

import { useGuardioStore } from "@/store/useGuardioStore";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)}GB`;
}

function StatCell({
  label,
  value,
  color,
}: {
  label: string;
  value: number | string;
  color: string;
}) {
  return (
    <div className="px-3 py-2.5">
      <div className="text-2xs font-mono text-text-dim mb-0.5">{label}</div>
      <div className={`text-sm font-mono font-medium tabular-nums ${color}`}>{value}</div>
    </div>
  );
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

  const isCritical = threatStatus === "CRITICAL";
  const isHigh = threatStatus === "HIGH";

  const levelColor =
    isCritical ? "#FF6B6B"
    : isHigh    ? "#FF9500"
    : threatStatus === "ELEVATED" ? "#FFCC66"
    : "#7CFFB2";

  return (
    <div className="flex-shrink-0 border-b border-bg-border">
      {/* Threat level — the dominant element */}
      <div className={`px-4 pt-4 pb-3 transition-colors duration-700 ${isCritical ? "bg-accent-red/[0.04]" : ""}`}>
        <div className="flex items-baseline gap-2 mb-1.5">
          <span
            className="text-5xl font-mono font-bold tabular-nums leading-none"
            style={{
              color: levelColor,
              textShadow: isCritical ? `0 0 28px ${levelColor}66` : undefined,
            }}
          >
            {threatLevel.toFixed(0)}
          </span>
          <span className="text-xl font-mono font-bold" style={{ color: levelColor }}>%</span>
          <span
            className={`ml-2 text-xs font-mono font-bold tracking-widest self-center ${
              isCritical ? "text-accent-red animate-pulse" : "text-text-muted"
            }`}
          >
            {threatStatus}
          </span>
        </div>
        {/* Threat bar — full width, glows when high */}
        <div className="relative h-[3px] bg-bg-border rounded-full overflow-hidden">
          <div
            className="absolute inset-y-0 left-0 rounded-full transition-all duration-700"
            style={{
              width: `${threatLevel}%`,
              background: levelColor,
              boxShadow: threatLevel > 50 ? `0 0 8px ${levelColor}88` : undefined,
            }}
          />
        </div>
      </div>

      {/* 4 key stats in a horizontal strip — no uniform grid, just data */}
      <div className="grid grid-cols-4 divide-x divide-bg-border border-t border-bg-border">
        <StatCell label="PKT" value={packetCount.toLocaleString()} color="text-accent-cyan" />
        <StatCell label="ALRT" value={alertCount} color={alertCount > 0 ? "text-accent-red" : "text-text-dim"} />
        <StatCell label="DROP" value={droppedCount} color={droppedCount > 0 ? "text-accent-yellow" : "text-text-dim"} />
        <StatCell label="COMP" value={compromisedCount} color={compromisedCount > 0 ? "text-accent-red" : "text-text-dim"} />
      </div>

      {/* Footer: sim status + data transferred on one line */}
      <div className="flex items-center gap-2 px-4 py-1.5 border-t border-bg-border">
        <span
          className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
            running ? "bg-accent-green animate-pulse-slow" : "bg-text-dim"
          }`}
        />
        <span className="text-2xs font-mono text-text-dim flex-1 truncate">
          {running ? (activeAttack && activeAttack !== "monitoring" ? activeAttack.toUpperCase() : "MONITORING") : "IDLE"}
        </span>
        <span className="text-2xs font-mono text-text-dim tabular-nums">{formatBytes(bytesTransferred)}</span>
      </div>

      {/* Active attack — shown only when an attack is running */}
      {activeAttack && activeAttack !== "monitoring" && (
        <div className="mx-3 mb-3 px-2.5 py-1.5 bg-accent-red/10 border border-accent-red/25 rounded flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-red animate-pulse flex-shrink-0" />
          <span className="text-2xs font-mono font-bold text-accent-red tracking-wider uppercase">
            {activeAttack}
          </span>
          <span className="text-2xs font-mono text-accent-red/50 ml-auto uppercase tracking-wide">ACTIVE</span>
        </div>
      )}
    </div>
  );
}
