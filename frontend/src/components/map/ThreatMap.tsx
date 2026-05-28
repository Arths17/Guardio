"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";
import { geoNaturalEarth1 } from "d3-geo";
import { useGuardioStore } from "@/store/useGuardioStore";
import type { ArcDatum, NodeData } from "@/types/events";
import clsx from "clsx";
import AlertFeed from "@/components/shared/AlertFeed";
import LiveMetrics from "@/components/shared/LiveMetrics";

const GEO_URL =
  "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

// Scale used by react-simple-maps "geoNaturalEarth1" by default
const RSM_DEFAULT_SCALE = 160;

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

const NODE_TYPE_RADIUS: Record<string, number> = {
  server: 4,
  database: 4.5,
  cloud: 5,
  client: 2.5,
  iot: 2.5,
};

// Quadratic bezier arc lifted toward the equatorial plane
function arcPath(
  srcLat: number,
  srcLng: number,
  dstLat: number,
  dstLng: number,
  proj: (coords: [number, number]) => [number, number] | null
): string | null {
  const src = proj([srcLng, srcLat]);
  const dst = proj([dstLng, dstLat]);
  if (!src || !dst) return null;

  const midLng = (srcLng + dstLng) / 2;
  const liftAmount = Math.abs(dstLng - srcLng) * 0.15;
  const midLat = (srcLat + dstLat) / 2 + liftAmount;
  const ctrl = proj([midLng, Math.max(-80, Math.min(80, midLat))]);
  if (!ctrl) return null;

  return `M ${src[0]} ${src[1]} Q ${ctrl[0]} ${ctrl[1]} ${dst[0]} ${dst[1]}`;
}

interface ArcLayer {
  arc: ArcDatum;
  path: string;
  key: string;
  startedAt: number;
}

interface SelectedNode {
  node: NodeData;
  x: number;
  y: number;
}

export default function ThreatMap() {
  const { arcs, nodes } = useGuardioStore();

  // Mirror react-simple-maps' internal projection so our arc math matches
  const [projFn, setProjFn] = useState<
    ((coords: [number, number]) => [number, number] | null) | null
  >(null);

  const [renderedArcs, setRenderedArcs] = useState<ArcLayer[]>([]);
  const [selectedNode, setSelectedNode] = useState<SelectedNode | null>(null);
  const [mapDims, setMapDims] = useState({ width: 800, height: 500 });
  const containerRef = useRef<HTMLDivElement>(null);

  // Measure container
  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setMapDims({ width: rect.width, height: rect.height });
      }
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Recreate projection whenever dims change — must match RSM's internal config
  useEffect(() => {
    const { width, height } = mapDims;
    const projection = geoNaturalEarth1()
      .scale(RSM_DEFAULT_SCALE)
      .translate([width / 2, height / 2])
      .rotate([0, 0, 0])
      .center([0, 0]);

    const fn = (coords: [number, number]): [number, number] | null => {
      const result = projection(coords);
      return result ?? null;
    };
    setProjFn(() => fn);
  }, [mapDims]);

  // Add incoming arcs
  useEffect(() => {
    if (!projFn || arcs.length === 0) return;
    const latest = arcs[0];
    if (!latest) return;

    const path = arcPath(
      latest.srcLat,
      latest.srcLng,
      latest.dstLat,
      latest.dstLng,
      projFn
    );
    if (!path) return;

    const key = `${latest.id}-${Date.now()}`;
    setRenderedArcs((prev) => {
      const filtered = prev.filter((a) => a.arc.id !== latest.id);
      return [{ arc: latest, path, key, startedAt: Date.now() }, ...filtered].slice(0, 80);
    });
  }, [arcs, projFn]);

  // Expire old arcs
  useEffect(() => {
    const interval = setInterval(() => {
      const cutoff = Date.now() - 4000;
      setRenderedArcs((prev) => prev.filter((a) => a.startedAt > cutoff));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleNodeClick = useCallback(
    (node: NodeData, e: React.MouseEvent) => {
      if (selectedNode?.node.id === node.id) {
        setSelectedNode(null);
        return;
      }
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      setSelectedNode({ node, x: e.clientX - rect.left, y: e.clientY - rect.top });
    },
    [selectedNode]
  );

  const { width, height } = mapDims;
  const mapNodes = Object.values(nodes);

  return (
    <div className="flex h-full overflow-hidden">
      {/* Map area */}
      <div
        ref={containerRef}
        className="relative flex-1 overflow-hidden bg-bg-base scanlines"
        onClick={() => setSelectedNode(null)}
      >
        {/* Subtle grid overlay */}
        <svg
          className="absolute inset-0 pointer-events-none z-0 opacity-15"
          width={width}
          height={height}
        >
          <defs>
            <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
              <path d="M 48 0 L 0 0 0 48" fill="none" stroke="#1E2A3A" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width={width} height={height} fill="url(#grid)" />
        </svg>

        {/* Map */}
        <ComposableMap
          projection="geoNaturalEarth1"
          projectionConfig={{ scale: RSM_DEFAULT_SCALE, center: [0, 0] }}
          width={width}
          height={height}
          style={{ width: "100%", height: "100%" }}
        >
          <ZoomableGroup>
            {/* Countries */}
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies.map((geo) => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="#0F172A"
                    stroke="#1E2A3A"
                    strokeWidth={0.4}
                    style={{
                      default: { outline: "none" },
                      hover:   { fill: "#111827", outline: "none" },
                      pressed: { outline: "none" },
                    }}
                  />
                ))
              }
            </Geographies>

            {/* Attack arcs */}
            {renderedArcs.map(({ arc, path, key, startedAt }) => {
              const age = Math.min(1, (Date.now() - startedAt) / 4000);
              const isHigh = arc.color === "#FF6B6B";
              return (
                <path
                  key={key}
                  d={path}
                  fill="none"
                  stroke={arc.color}
                  strokeWidth={isHigh ? 1.5 : 1}
                  strokeOpacity={Math.max(0, 0.9 - age * 0.6)}
                  className={isHigh ? "arc-path-fast" : "arc-path"}
                  style={{ filter: `drop-shadow(0 0 3px ${arc.color}66)` }}
                />
              );
            })}

            {/* Nodes */}
            {projFn &&
              mapNodes.map((node) => {
                const pt = projFn([node.lng, node.lat]);
                if (!pt) return null;
                const [x, y] = pt;
                const color = NODE_STATE_COLORS[node.state] ?? "#7CFFB2";
                const r = NODE_TYPE_RADIUS[node.type] ?? 3;
                const isSelected = selectedNode?.node.id === node.id;
                const isActive = node.state !== "healthy" && node.state !== "offline";

                return (
                  <g
                    key={node.id}
                    transform={`translate(${x},${y})`}
                    style={{ cursor: "pointer" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleNodeClick(node, e as unknown as React.MouseEvent);
                    }}
                  >
                    {isActive && (
                      <circle r={r + 6} fill="none" stroke={color} strokeWidth={1} opacity={0} className="pulse-ring" />
                    )}
                    {isSelected && (
                      <circle r={r + 4} fill="none" stroke={color} strokeWidth={1.5} opacity={0.6} />
                    )}
                    <circle
                      r={r}
                      fill={color}
                      fillOpacity={node.state === "offline" ? 0.3 : 0.9}
                      stroke={color}
                      strokeWidth={0.5}
                      style={isActive ? { filter: `drop-shadow(0 0 4px ${color}88)` } : undefined}
                      className={node.state === "encrypted" ? "node-blink" : undefined}
                    />
                  </g>
                );
              })}
          </ZoomableGroup>
        </ComposableMap>

        {/* Empty state */}
        {Object.keys(nodes).length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center space-y-1">
              <div className="text-xs font-mono text-text-muted">AWAITING TOPOLOGY</div>
              <div className="text-2xs font-mono text-text-dim">Start simulation to stream live data</div>
            </div>
          </div>
        )}

        {/* Node tooltip */}
        {selectedNode && (
          <NodeTooltip
            node={selectedNode.node}
            x={selectedNode.x}
            y={selectedNode.y}
            onClose={() => setSelectedNode(null)}
          />
        )}

        {/* Map legend */}
        <MapLegend />

        {/* Arc counter */}
        <div className="absolute top-3 left-3 pointer-events-none">
          <div className="flex items-center gap-1.5 px-2 py-1 bg-bg-overlay/80 border border-bg-border rounded text-2xs font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan animate-pulse-slow" />
            <span className="text-text-muted">ARCS</span>
            <span className="text-accent-cyan tabular-nums">{renderedArcs.length}</span>
          </div>
        </div>
      </div>

      {/* Right panel */}
      <aside className="w-72 flex flex-col bg-bg-surface border-l border-bg-border overflow-hidden flex-shrink-0">
        <LiveMetrics />
        <div className="flex-1 overflow-hidden">
          <AlertFeed />
        </div>
      </aside>
    </div>
  );
}

function MapLegend() {
  const states = [
    { label: "Healthy",     color: "#7CFFB2" },
    { label: "Probing",     color: "#FFCC66" },
    { label: "Stressed",    color: "#FF9500" },
    { label: "Compromised", color: "#FF6B6B" },
    { label: "Encrypted",   color: "#A78BFA" },
    { label: "Recovering",  color: "#00C2FF" },
  ];
  return (
    <div className="absolute bottom-3 left-3 bg-bg-overlay/80 border border-bg-border rounded px-2.5 py-2 flex flex-col gap-1">
      {states.map((s) => (
        <div key={s.label} className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: s.color }} />
          <span className="text-2xs font-mono text-text-muted">{s.label}</span>
        </div>
      ))}
    </div>
  );
}

function NodeTooltip({
  node,
  x,
  y,
  onClose,
}: {
  node: NodeData;
  x: number;
  y: number;
  onClose: () => void;
}) {
  const color = NODE_STATE_COLORS[node.state] ?? "#7CFFB2";
  const loadPct = Math.round(node.load * 100);

  return (
    <div
      className="absolute z-30 w-52 bg-bg-overlay border border-bg-border rounded shadow-xl animate-fade-in pointer-events-auto"
      style={{ left: x + 12, top: y - 8 }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-start justify-between px-3 pt-2.5 pb-1.5 border-b border-bg-border">
        <div>
          <div className="text-xs font-medium text-text-primary leading-tight">{node.name}</div>
          <div className="text-2xs font-mono text-text-muted mt-0.5 uppercase">{node.type} · {node.zone}</div>
        </div>
        <button onClick={onClose} className="text-text-muted hover:text-text-secondary ml-2 mt-0.5 p-0.5">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" />
          </svg>
        </button>
      </div>
      <div className="px-3 py-2 space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-2xs font-mono text-text-muted">STATE</span>
          <span className="text-2xs font-mono font-medium" style={{ color }}>
            {node.state.toUpperCase()}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-2xs font-mono text-text-muted">LOAD</span>
          <div className="flex items-center gap-1.5">
            <div className="w-16 h-1 bg-bg-border rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${loadPct}%`,
                  background: loadPct > 80 ? "#FF6B6B" : loadPct > 50 ? "#FF9500" : "#7CFFB2",
                }}
              />
            </div>
            <span className="text-2xs font-mono text-text-secondary tabular-nums">{loadPct}%</span>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-2xs font-mono text-text-muted">ID</span>
          <span className="text-2xs font-mono text-text-dim">{node.id}</span>
        </div>
        {node.services.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-0.5">
            {node.services.slice(0, 4).map((s) => (
              <span key={s} className="text-2xs font-mono px-1 py-0.5 bg-bg-border rounded text-text-muted">
                {s}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
