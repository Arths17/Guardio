"use client";

import { useState } from "react";
import { useGuardioStore, type IncidentEntry } from "@/store/useGuardioStore";
import { format } from "date-fns";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

const SEV_CONFIG = {
  critical: { dot: "bg-accent-red", border: "border-l-accent-red", label: "CRIT", labelColor: "text-accent-red", bg: "bg-accent-red/5" },
  high:     { dot: "bg-accent-orange", border: "border-l-accent-orange", label: "HIGH", labelColor: "text-accent-orange", bg: "bg-accent-orange/5" },
  medium:   { dot: "bg-accent-yellow", border: "border-l-accent-yellow", label: "MED", labelColor: "text-accent-yellow", bg: "" },
  low:      { dot: "bg-accent-green", border: "border-l-text-muted", label: "LOW", labelColor: "text-accent-green", bg: "" },
};

const TYPE_ICONS: Record<string, string> = {
  attack: "⚡",
  attack_phase: "⚡",
  alert: "🔴",
  node_state: "⬡",
  defense: "🛡",
  dropped: "↓",
  honeypot: "🍯",
};

type FilterType = "all" | "attack" | "alert" | "node_state" | "defense";

export default function IncidentTimeline() {
  const incidents = useGuardioStore((s) => s.incidents);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>("all");
  const [search, setSearch] = useState("");

  const filtered = incidents.filter((inc) => {
    if (filter !== "all") {
      if (filter === "attack" && !inc.type.startsWith("attack")) return false;
      if (filter !== "attack" && inc.type !== filter) return false;
    }
    if (search && !inc.title.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const FILTERS: { id: FilterType; label: string }[] = [
    { id: "all", label: "All" },
    { id: "attack", label: "Attacks" },
    { id: "alert", label: "IDS" },
    { id: "node_state", label: "Nodes" },
    { id: "defense", label: "Defense" },
  ];

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-bg-border flex-shrink-0 bg-bg-surface">
          <span className="text-xs font-mono font-medium text-text-secondary uppercase tracking-widest mr-1">
            Incident Timeline
          </span>
          <div className="flex items-center gap-1">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={clsx(
                  "px-2 py-0.5 text-2xs font-mono rounded border transition-colors",
                  filter === f.id
                    ? "border-accent-cyan text-accent-cyan bg-accent-cyan/10"
                    : "border-bg-border text-text-muted hover:border-text-muted"
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="flex-1" />
          <input
            type="text"
            placeholder="Search events…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-40 px-2 py-0.5 text-2xs font-mono bg-bg-elevated border border-bg-border rounded text-text-secondary placeholder-text-dim focus:outline-none focus:border-accent-cyan/50"
          />
          <span className="text-2xs font-mono text-text-dim tabular-nums">{filtered.length} events</span>
        </div>

        {/* Events */}
        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-xs font-mono text-text-dim">
              {incidents.length === 0 ? "No events yet — start simulation" : "No matches"}
            </div>
          ) : (
            <div className="relative">
              {/* Timeline spine */}
              <div className="absolute left-[31px] top-0 bottom-0 w-px bg-bg-border" />

              {filtered.map((inc, idx) => (
                <IncidentRow
                  key={inc.id}
                  inc={inc}
                  isFirst={idx === 0}
                  expanded={expanded === inc.id}
                  onToggle={() => setExpanded(expanded === inc.id ? null : inc.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Stats sidebar */}
      <aside className="w-56 bg-bg-surface border-l border-bg-border flex flex-col overflow-hidden flex-shrink-0">
        <div className="px-3 py-2.5 border-b border-bg-border">
          <span className="text-2xs font-mono font-medium text-text-secondary uppercase tracking-widest">
            Breakdown
          </span>
        </div>
        <TimelineStats incidents={incidents} />
      </aside>
    </div>
  );
}

function IncidentRow({
  inc,
  isFirst,
  expanded,
  onToggle,
}: {
  inc: IncidentEntry;
  isFirst: boolean;
  expanded: boolean;
  onToggle: () => void;
}) {
  const sev = SEV_CONFIG[inc.severity] ?? SEV_CONFIG.low;
  const icon = TYPE_ICONS[inc.type] ?? "·";

  let timeStr = "";
  try {
    timeStr = format(new Date(inc.ts), "HH:mm:ss.SSS");
  } catch {
    timeStr = inc.ts;
  }

  return (
    <div
      className={clsx(
        "flex gap-0 border-l-2 transition-colors",
        expanded ? sev.border + " " + sev.bg : "border-l-transparent hover:border-l-bg-border hover:bg-bg-surface/50",
        isFirst && "animate-fade-in"
      )}
    >
      {/* Timeline dot */}
      <div className="flex flex-col items-center pt-4 pl-6 pr-3 flex-shrink-0">
        <div className={clsx("w-2 h-2 rounded-full flex-shrink-0 z-10", sev.dot)} />
      </div>

      {/* Content */}
      <button
        onClick={onToggle}
        className="flex-1 text-left py-2.5 pr-4 min-w-0"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-1.5 min-w-0 flex-1">
            <span className="text-xs flex-shrink-0">{icon}</span>
            <span className="text-xs text-text-primary leading-tight truncate">{inc.title}</span>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <span className={clsx("text-2xs font-mono font-medium", sev.labelColor)}>{sev.label}</span>
            <span className="text-2xs font-mono text-text-dim tabular-nums">{timeStr}</span>
          </div>
        </div>

        {inc.detail && (
          <div className="text-2xs text-text-muted mt-0.5 ml-5 truncate">{inc.detail}</div>
        )}

        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden"
            >
              <ForensicData raw={inc.raw} />
            </motion.div>
          )}
        </AnimatePresence>
      </button>
    </div>
  );
}

function ForensicData({ raw }: { raw: Record<string, unknown> }) {
  const entries = Object.entries(raw).filter(
    ([k]) => !["ts", "type"].includes(k)
  );

  if (entries.length === 0) return null;

  return (
    <div className="mt-2 ml-5 p-2 bg-bg-elevated border border-bg-border rounded text-2xs font-mono">
      {entries.map(([k, v]) => (
        <div key={k} className="flex gap-2 py-0.5">
          <span className="text-text-muted w-28 flex-shrink-0">{k}</span>
          <span className="text-text-secondary truncate">
            {typeof v === "object" ? JSON.stringify(v).slice(0, 80) : String(v)}
          </span>
        </div>
      ))}
    </div>
  );
}

function TimelineStats({ incidents }: { incidents: IncidentEntry[] }) {
  const bySev: Record<string, number> = {};
  const byType: Record<string, number> = {};

  for (const inc of incidents) {
    bySev[inc.severity] = (bySev[inc.severity] || 0) + 1;
    const typeKey = inc.type.startsWith("attack") ? "attack" : inc.type;
    byType[typeKey] = (byType[typeKey] || 0) + 1;
  }

  const attackNames = Array.from(
    new Set(
      incidents
        .filter((i) => i.type === "attack")
        .map((i) => i.raw.name as string)
        .filter(Boolean)
    )
  );

  return (
    <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
      <div>
        <div className="text-2xs font-mono text-text-muted mb-2">BY SEVERITY</div>
        {(["critical", "high", "medium", "low"] as const).map((sev) => {
          const count = bySev[sev] || 0;
          if (!count) return null;
          const cfg = SEV_CONFIG[sev];
          return (
            <div key={sev} className="flex justify-between py-0.5">
              <span className={clsx("text-2xs font-mono", cfg.labelColor)}>{sev.toUpperCase()}</span>
              <span className="text-2xs font-mono text-text-secondary tabular-nums">{count}</span>
            </div>
          );
        })}
      </div>

      {attackNames.length > 0 && (
        <div>
          <div className="text-2xs font-mono text-text-muted mb-2">ATTACK TYPES</div>
          {attackNames.map((name) => (
            <div key={name} className="flex justify-between py-0.5">
              <span className="text-2xs font-mono text-accent-orange">{name}</span>
            </div>
          ))}
        </div>
      )}

      <div>
        <div className="text-2xs font-mono text-text-muted mb-2">BY CATEGORY</div>
        {Object.entries(byType)
          .sort(([, a], [, b]) => b - a)
          .map(([type, count]) => (
            <div key={type} className="flex justify-between py-0.5">
              <span className="text-2xs font-mono text-text-secondary">{type}</span>
              <span className="text-2xs font-mono text-text-secondary tabular-nums">{count}</span>
            </div>
          ))}
      </div>

      <div className="pt-1 border-t border-bg-border">
        <div className="flex justify-between">
          <span className="text-2xs font-mono text-text-muted">TOTAL</span>
          <span className="text-2xs font-mono text-text-primary tabular-nums">{incidents.length}</span>
        </div>
      </div>
    </div>
  );
}
