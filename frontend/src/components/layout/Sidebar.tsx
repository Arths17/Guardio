"use client";

import { motion } from "framer-motion";
import clsx from "clsx";

export type ViewId = "map" | "graph" | "timeline" | "intel" | "ai";

interface NavItem {
  id: ViewId;
  label: string;
  icon: React.ReactNode;
}

const GlobeIcon = () => (
  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3.6 9h16.8M3.6 15h16.8M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" />
  </svg>
);

const GraphIcon = () => (
  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <circle cx="5" cy="12" r="2" />
    <circle cx="19" cy="5" r="2" />
    <circle cx="19" cy="19" r="2" />
    <circle cx="12" cy="12" r="2" />
    <path d="M7 12h3M14 12h3M13.4 10.6 17 7M13.4 13.4 17 17" />
  </svg>
);

const TimelineIcon = () => (
  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" strokeLinecap="round" />
  </svg>
);

const IntelIcon = () => (
  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path d="M9 19v-6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2zm0 0V9a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v10m-6 0a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2m0 0V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2z" />
  </svg>
);

const AIIcon = () => (
  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path d="M9.663 17h4.673M12 3v1m6.364 1.636-.707.707M21 12h-1M4 12H3m3.343-5.657-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const NAV: NavItem[] = [
  { id: "map", label: "Threat Map", icon: <GlobeIcon /> },
  { id: "graph", label: "Infra Graph", icon: <GraphIcon /> },
  { id: "timeline", label: "Timeline", icon: <TimelineIcon /> },
  { id: "intel", label: "Intelligence", icon: <IntelIcon /> },
  { id: "ai", label: "AI Copilot", icon: <AIIcon /> },
];

interface Props {
  active: ViewId;
  onChange: (v: ViewId) => void;
}

export default function Sidebar({ active, onChange }: Props) {
  return (
    <nav className="flex flex-col items-center py-3 gap-1 w-[52px] bg-bg-surface border-r border-bg-border flex-shrink-0">
      {/* Logo mark */}
      <div className="mb-4 mt-1 flex items-center justify-center">
        <div className="w-7 h-7 relative">
          <svg viewBox="0 0 28 28" fill="none">
            <path
              d="M14 2L4 7v7c0 5.5 4.3 10.6 10 12 5.7-1.4 10-6.5 10-12V7L14 2z"
              fill="#00C2FF"
              fillOpacity={0.12}
              stroke="#00C2FF"
              strokeWidth={1.5}
            />
            <path
              d="M10 14l3 3 5-5"
              stroke="#00C2FF"
              strokeWidth={1.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>

      <div className="w-5 h-px bg-bg-border mb-2" />

      {NAV.map((item) => {
        const isActive = item.id === active;
        return (
          <button
            key={item.id}
            onClick={() => onChange(item.id)}
            title={item.label}
            className={clsx(
              "relative w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-150 group",
              isActive
                ? "bg-accent-cyan/10 text-accent-cyan"
                : "text-text-muted hover:text-text-secondary hover:bg-bg-elevated"
            )}
          >
            {isActive && (
              <motion.div
                layoutId="sidebar-indicator"
                className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-accent-cyan rounded-r-full"
                transition={{ type: "spring", stiffness: 400, damping: 35 }}
              />
            )}
            {item.icon}
            {/* Tooltip */}
            <span className="absolute left-full ml-2 px-2 py-1 text-2xs font-mono bg-bg-overlay border border-bg-border rounded text-text-secondary whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
              {item.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
