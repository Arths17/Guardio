"use client";

import { useMemo } from "react";
import { useGuardioStore } from "@/store/useGuardioStore";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import clsx from "clsx";

const NODE_STATE_COLORS: Record<string, string> = {
  healthy: "#7CFFB2",
  probing: "#FFCC66",
  stressed: "#FF9500",
  compromised: "#FF6B6B",
  encrypted: "#A78BFA",
  recovering: "#00C2FF",
  isolated: "#64748B",
  offline: "#374151",
};

const PROTOCOL_COLORS: Record<string, string> = {
  "TCP-SYN": "#FF6B6B",
  "UDP-FLOOD": "#FF9500",
  "ICMP-FLOOD": "#FFCC66",
  "SMB": "#FF6B6B",
  "RDP": "#FF9500",
  "HTTPS": "#00C2FF",
  "HTTP/1.1": "#7CFFB2",
  "DNS": "#7CFFB2",
  "TCP": "#94A3B8",
  "UDP": "#94A3B8",
};

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="px-4 py-2 border-b border-bg-border bg-bg-surface">
      <span className="text-2xs font-mono font-medium text-text-secondary uppercase tracking-widest">
        {title}
      </span>
    </div>
  );
}

function MetricCard({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-bg-surface border border-bg-border rounded p-3 flex flex-col gap-1">
      <span className="text-2xs font-mono text-text-muted uppercase">{label}</span>
      <span className={clsx("text-xl font-mono font-medium tabular-nums leading-none", color ?? "text-text-primary")}>
        {value}
      </span>
      {sub && <span className="text-2xs font-mono text-text-dim">{sub}</span>}
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-bg-overlay border border-bg-border rounded px-2 py-1.5">
      <div className="text-2xs font-mono text-text-secondary">{label}</div>
      <div className="text-xs font-mono text-text-primary">{payload[0].value}</div>
    </div>
  );
};

export default function ThreatIntelPanel() {
  const {
    protocolStats,
    alerts,
    nodes,
    packetCount,
    alertCount,
    droppedCount,
    bytesTransferred,
    attackLog,
    defenseActions,
  } = useGuardioStore();

  // Protocol breakdown (top 10)
  const protocolData = useMemo(() => {
    return Object.entries(protocolStats)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([name, count]) => ({ name, count }));
  }, [protocolStats]);

  // Node state distribution
  const nodeStateData = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const n of Object.values(nodes)) {
      counts[n.state] = (counts[n.state] || 0) + 1;
    }
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .map(([state, count]) => ({ state, count }));
  }, [nodes]);

  // Top alert sources
  const topSources = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const a of alerts) {
      counts[a.src] = (counts[a.src] || 0) + 1;
    }
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8)
      .map(([src, count]) => ({ src, count }));
  }, [alerts]);

  // Attack type summary
  const attackSummary = useMemo(() => {
    const names: Record<string, number> = {};
    for (const ev of attackLog) {
      if (ev.stage === "start") names[ev.name] = (names[ev.name] || 0) + 1;
    }
    return Object.entries(names).sort(([, a], [, b]) => b - a);
  }, [attackLog]);

  const compromisedCount = Object.values(nodes).filter(
    (n) => n.state === "compromised" || n.state === "encrypted"
  ).length;

  const critCount = alerts.filter((a) => a.level === "critical").length;

  function fmtBytes(b: number): string {
    if (b < 1024) return `${b}B`;
    if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)}K`;
    if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)}M`;
    return `${(b / 1024 / 1024 / 1024).toFixed(2)}G`;
  }

  return (
    <div className="h-full overflow-y-auto bg-bg-base">
      <div className="p-4 space-y-4">

        {/* Summary metrics row */}
        <div className="grid grid-cols-5 gap-3">
          <MetricCard
            label="Packets"
            value={packetCount.toLocaleString()}
            color="text-accent-cyan"
          />
          <MetricCard
            label="Alerts"
            value={alertCount}
            sub={`${critCount} critical`}
            color={alertCount > 0 ? "text-accent-red" : "text-text-muted"}
          />
          <MetricCard
            label="Compromised"
            value={compromisedCount}
            color={compromisedCount > 0 ? "text-accent-red" : "text-text-muted"}
          />
          <MetricCard
            label="Dropped"
            value={droppedCount}
            color={droppedCount > 0 ? "text-accent-yellow" : "text-text-muted"}
          />
          <MetricCard
            label="Data"
            value={fmtBytes(bytesTransferred)}
            color="text-text-primary"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Protocol breakdown */}
          <div className="bg-bg-surface border border-bg-border rounded overflow-hidden">
            <SectionHeader title="Protocol Distribution" />
            <div className="p-3">
              {protocolData.length === 0 ? (
                <div className="flex items-center justify-center h-32 text-2xs font-mono text-text-dim">NO DATA</div>
              ) : (
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={protocolData} layout="vertical" margin={{ left: 0, right: 8, top: 0, bottom: 0 }}>
                    <XAxis type="number" tick={{ fill: "#475569", fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={80}
                      tick={{ fill: "#94A3B8", fontSize: 9, fontFamily: "JetBrains Mono" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: "#1E2A3A" }} />
                    <Bar dataKey="count" radius={[0, 2, 2, 0]}>
                      {protocolData.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={PROTOCOL_COLORS[entry.name] ?? "#00C2FF"}
                          fillOpacity={0.8}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Node state distribution */}
          <div className="bg-bg-surface border border-bg-border rounded overflow-hidden">
            <SectionHeader title="Infrastructure State" />
            <div className="p-3">
              {nodeStateData.length === 0 ? (
                <div className="flex items-center justify-center h-32 text-2xs font-mono text-text-dim">NO DATA</div>
              ) : (
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={nodeStateData} layout="vertical" margin={{ left: 0, right: 8, top: 0, bottom: 0 }}>
                    <XAxis type="number" tick={{ fill: "#475569", fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
                    <YAxis
                      type="category"
                      dataKey="state"
                      width={80}
                      tick={{ fill: "#94A3B8", fontSize: 9, fontFamily: "JetBrains Mono" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: "#1E2A3A" }} />
                    <Bar dataKey="count" radius={[0, 2, 2, 0]}>
                      {nodeStateData.map((entry) => (
                        <Cell
                          key={entry.state}
                          fill={NODE_STATE_COLORS[entry.state] ?? "#94A3B8"}
                          fillOpacity={0.8}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Top alert sources */}
          <div className="bg-bg-surface border border-bg-border rounded overflow-hidden">
            <SectionHeader title="Top Alert Sources" />
            <div className="divide-y divide-bg-border">
              {topSources.length === 0 ? (
                <div className="flex items-center justify-center h-16 text-2xs font-mono text-text-dim">NO DATA</div>
              ) : (
                topSources.map(({ src, count }, i) => (
                  <div key={src} className="flex items-center gap-2 px-3 py-2">
                    <span className="text-2xs font-mono text-text-dim w-4 tabular-nums">{i + 1}</span>
                    <span className="text-2xs font-mono text-text-secondary flex-1 truncate">{src}</span>
                    <span className="text-2xs font-mono text-accent-red tabular-nums">{count}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Attack log */}
          <div className="bg-bg-surface border border-bg-border rounded overflow-hidden">
            <SectionHeader title="Attack Summary" />
            <div className="p-3 space-y-2">
              {attackSummary.length === 0 ? (
                <div className="flex items-center justify-center h-16 text-2xs font-mono text-text-dim">NO ATTACKS</div>
              ) : (
                attackSummary.map(([name, count]) => (
                  <div key={name} className="flex items-center justify-between">
                    <span className="text-2xs font-mono text-accent-orange uppercase">{name}</span>
                    <span className="text-2xs font-mono text-text-secondary tabular-nums">{count}x</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Defense actions */}
          <div className="bg-bg-surface border border-bg-border rounded overflow-hidden">
            <SectionHeader title="Defense Actions" />
            <div className="divide-y divide-bg-border overflow-y-auto max-h-48">
              {defenseActions.length === 0 ? (
                <div className="flex items-center justify-center h-16 text-2xs font-mono text-text-dim">NO ACTIONS</div>
              ) : (
                defenseActions.slice(0, 10).map((da, i) => (
                  <div key={i} className="px-3 py-1.5">
                    <div className="text-2xs font-mono text-accent-green">{da.action}</div>
                    {da.target && (
                      <div className="text-2xs font-mono text-text-dim truncate">{da.target}</div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Recent IDS alerts table */}
        <div className="bg-bg-surface border border-bg-border rounded overflow-hidden">
          <SectionHeader title="Recent IDS Detections" />
          <div className="overflow-x-auto">
            <table className="w-full text-2xs font-mono">
              <thead>
                <tr className="border-b border-bg-border">
                  <th className="text-left px-3 py-2 text-text-muted font-medium">LEVEL</th>
                  <th className="text-left px-3 py-2 text-text-muted font-medium">REASON</th>
                  <th className="text-left px-3 py-2 text-text-muted font-medium">SRC</th>
                  <th className="text-left px-3 py-2 text-text-muted font-medium">DST</th>
                  <th className="text-left px-3 py-2 text-text-muted font-medium">PROTO</th>
                  <th className="text-right px-3 py-2 text-text-muted font-medium">SCORE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-bg-border">
                {alerts.slice(0, 12).map((a) => (
                  <tr key={a.alert_id} className="hover:bg-bg-elevated transition-colors">
                    <td className="px-3 py-1.5">
                      <span
                        className={clsx(
                          "font-medium",
                          a.level === "critical"
                            ? "text-accent-red"
                            : a.level === "high"
                            ? "text-accent-orange"
                            : "text-accent-yellow"
                        )}
                      >
                        {a.level.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 text-text-secondary max-w-[200px] truncate">{a.reason}</td>
                    <td className="px-3 py-1.5 text-text-dim truncate max-w-[120px]">{a.src}</td>
                    <td className="px-3 py-1.5 text-text-dim truncate max-w-[120px]">{a.dst}</td>
                    <td className="px-3 py-1.5">
                      <span className="px-1 py-0.5 bg-bg-border rounded">{a.protocol}</span>
                    </td>
                    <td className="px-3 py-1.5 text-right text-accent-cyan tabular-nums">
                      {a.score.toFixed(3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {alerts.length === 0 && (
              <div className="flex items-center justify-center py-8 text-2xs font-mono text-text-dim">
                No detections
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
