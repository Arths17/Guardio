"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useGuardioStore } from "@/store/useGuardioStore";
import type { NodeData } from "@/types/events";
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

const ZONE_ORDER = ["external", "dmz", "internal", "data", "cloud", "iot"];

const ZONE_COLORS: Record<string, string> = {
  external: "#1E3A5F",
  dmz:      "#1A3A2A",
  internal: "#2A1A3A",
  data:     "#3A1A1A",
  cloud:    "#1A2A3A",
  iot:      "#3A2A1A",
};

type FilterZone = "all" | "external" | "dmz" | "internal" | "data" | "cloud" | "iot";

interface GraphNode {
  id: string;
  name: string;
  type: string;
  zone: string;
  state: string;
  load: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface GraphEdge {
  source: string;
  target: string;
}

// Derive edges from zone relationships and known service topology
function buildEdges(nodes: Record<string, NodeData>): GraphEdge[] {
  const edges: GraphEdge[] = [];
  const nodeList = Object.values(nodes);

  const byZone: Record<string, string[]> = {};
  for (const n of nodeList) {
    byZone[n.zone] = byZone[n.zone] || [];
    byZone[n.zone].push(n.id);
  }

  // Connect servers to databases
  const servers = nodeList.filter((n) => n.type === "server").map((n) => n.id);
  const dbs = nodeList.filter((n) => n.type === "database").map((n) => n.id);
  for (const s of servers.slice(0, 6)) {
    for (const d of dbs) {
      edges.push({ source: s, target: d });
    }
  }

  // Connect clients to servers (sample)
  const clients = nodeList.filter((n) => n.type === "client").slice(0, 20).map((n) => n.id);
  const webServers = servers.slice(0, 4);
  for (const c of clients) {
    const target = webServers[Math.floor(Math.random() * webServers.length)];
    if (target) edges.push({ source: c, target });
  }

  // Servers to cloud
  const clouds = nodeList.filter((n) => n.type === "cloud").map((n) => n.id);
  for (const s of servers.slice(0, 4)) {
    for (const c of clouds) {
      edges.push({ source: s, target: c });
    }
  }

  // IoT to servers (indirect)
  const iots = nodeList.filter((n) => n.type === "iot").map((n) => n.id);
  const apiGw = servers.find((s) => s === "srv-3") || servers[0];
  if (apiGw) {
    for (const iot of iots) {
      edges.push({ source: iot, target: apiGw });
    }
  }

  return edges;
}

// Simple force-directed layout computed in JS (no canvas library dependency)
function initPositions(nodes: GraphNode[], width: number, height: number): void {
  const byZone: Record<string, GraphNode[]> = {};
  for (const n of nodes) {
    byZone[n.zone] = byZone[n.zone] || [];
    byZone[n.zone].push(n);
  }
  const zones = ZONE_ORDER.filter((z) => byZone[z]?.length > 0);
  const colW = width / (zones.length + 1);

  zones.forEach((zone, zi) => {
    const zNodes = byZone[zone] || [];
    const cx = colW * (zi + 1);
    zNodes.forEach((n, i) => {
      const rows = zNodes.length;
      const rowH = height / (rows + 1);
      n.x = cx + (Math.random() - 0.5) * 40;
      n.y = rowH * (i + 1) + (Math.random() - 0.5) * 20;
      n.vx = 0;
      n.vy = 0;
    });
  });
}

function runForce(
  nodes: GraphNode[],
  edges: GraphEdge[],
  width: number,
  height: number,
  iterations = 30
): void {
  const nodeMap: Record<string, GraphNode> = {};
  for (const n of nodes) nodeMap[n.id] = n;

  for (let iter = 0; iter < iterations; iter++) {
    const alpha = 1 - iter / iterations;

    // Repulsion
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (50 * 50) / dist;
        const fx = (dx / dist) * force * alpha * 0.1;
        const fy = (dy / dist) * force * alpha * 0.1;
        a.vx += fx;
        a.vy += fy;
        b.vx -= fx;
        b.vy -= fy;
      }
    }

    // Attraction (edges)
    for (const e of edges) {
      const a = nodeMap[e.source], b = nodeMap[e.target];
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (dist - 100) * 0.03 * alpha;
      a.vx += (dx / dist) * force;
      a.vy += (dy / dist) * force;
      b.vx -= (dx / dist) * force;
      b.vy -= (dy / dist) * force;
    }

    // Apply + bounds
    for (const n of nodes) {
      n.x = Math.max(20, Math.min(width - 20, n.x + n.vx));
      n.y = Math.max(20, Math.min(height - 20, n.y + n.vy));
      n.vx *= 0.7;
      n.vy *= 0.7;
    }
  }
}

export default function InfraGraph() {
  const { nodes } = useGuardioStore();
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 900, height: 600 });
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [filterZone, setFilterZone] = useState<FilterZone>("all");
  const [viewBox, setViewBox] = useState({ x: 0, y: 0, scale: 1 });
  const edgesRef = useRef<GraphEdge[]>([]);

  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        const r = containerRef.current.getBoundingClientRect();
        setDims({ width: r.width, height: r.height });
      }
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Build graph when nodes change
  useEffect(() => {
    const nodeList = Object.values(nodes);
    if (nodeList.length === 0) return;

    const gNodes: GraphNode[] = nodeList.map((n) => ({
      id: n.id,
      name: n.name,
      type: n.type,
      zone: n.zone,
      state: n.state,
      load: n.load,
      x: 0,
      y: 0,
      vx: 0,
      vy: 0,
    }));

    initPositions(gNodes, dims.width, dims.height);
    const gEdges = buildEdges(nodes);
    edgesRef.current = gEdges;
    runForce(gNodes, gEdges, dims.width, dims.height, 60);
    setGraphNodes(gNodes);
    setEdges(gEdges);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [Object.keys(nodes).length, dims.width, dims.height]);

  // Update state/load without re-running force layout
  useEffect(() => {
    setGraphNodes((prev) =>
      prev.map((gn) => {
        const live = nodes[gn.id];
        if (!live) return gn;
        return { ...gn, state: live.state, load: live.load };
      })
    );
  }, [nodes]);

  const filteredNodes =
    filterZone === "all" ? graphNodes : graphNodes.filter((n) => n.zone === filterZone);
  const filteredIds = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = edges.filter(
    (e) => filteredIds.has(e.source) && filteredIds.has(e.target)
  );

  const nodeMap: Record<string, GraphNode> = {};
  for (const n of graphNodes) nodeMap[n.id] = n;

  const zones = Array.from(new Set(graphNodes.map((n) => n.zone))).filter(Boolean) as string[];

  return (
    <div className="flex h-full overflow-hidden">
      <div ref={containerRef} className="relative flex-1 bg-bg-base overflow-hidden">
        {/* Zone filter */}
        <div className="absolute top-3 left-3 z-10 flex items-center gap-1 flex-wrap">
          {(["all", ...zones] as FilterZone[]).map((z) => (
            <button
              key={z}
              onClick={() => setFilterZone(z)}
              className={clsx(
                "px-2 py-0.5 text-2xs font-mono rounded border transition-colors",
                filterZone === z
                  ? "border-accent-cyan text-accent-cyan bg-accent-cyan/10"
                  : "border-bg-border text-text-muted hover:border-text-muted"
              )}
            >
              {z.toUpperCase()}
            </button>
          ))}
        </div>

        <svg
          ref={svgRef}
          width={dims.width}
          height={dims.height}
          className="w-full h-full"
          onClick={() => setSelected(null)}
        >
          {/* Zone backgrounds */}
          {zones.map((zone) => {
            const zNodes = filteredNodes.filter((n) => n.zone === zone);
            if (zNodes.length === 0) return null;
            const xs = zNodes.map((n) => n.x);
            const ys = zNodes.map((n) => n.y);
            const minX = Math.min(...xs) - 30;
            const maxX = Math.max(...xs) + 30;
            const minY = Math.min(...ys) - 30;
            const maxY = Math.max(...ys) + 30;
            return (
              <g key={zone}>
                <rect
                  x={minX}
                  y={minY}
                  width={maxX - minX}
                  height={maxY - minY}
                  rx={8}
                  fill={ZONE_COLORS[zone] ?? "#1E2A3A"}
                  fillOpacity={0.25}
                  stroke="#1E2A3A"
                  strokeWidth={1}
                />
                <text
                  x={minX + 8}
                  y={minY + 14}
                  fill="#475569"
                  fontSize={9}
                  fontFamily="JetBrains Mono, monospace"
                  letterSpacing={2}
                >
                  {zone.toUpperCase()}
                </text>
              </g>
            );
          })}

          {/* Edges */}
          {filteredEdges.map((e, i) => {
            const a = nodeMap[e.source];
            const b = nodeMap[e.target];
            if (!a || !b) return null;
            const isCompromised =
              a.state === "compromised" || b.state === "compromised" ||
              a.state === "encrypted" || b.state === "encrypted";
            return (
              <line
                key={i}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={isCompromised ? "#FF6B6B" : "#1E2A3A"}
                strokeWidth={isCompromised ? 1.5 : 0.75}
                strokeOpacity={isCompromised ? 0.6 : 0.4}
              />
            );
          })}

          {/* Nodes */}
          {filteredNodes.map((n) => {
            const color = NODE_STATE_COLORS[n.state] ?? "#7CFFB2";
            const r = n.type === "server" || n.type === "database" ? 7 : n.type === "cloud" ? 9 : 5;
            const isSelected = selected?.id === n.id;
            const isActive = n.state !== "healthy" && n.state !== "offline";

            return (
              <g
                key={n.id}
                transform={`translate(${n.x},${n.y})`}
                style={{ cursor: "pointer" }}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelected(isSelected ? null : n);
                }}
              >
                {isActive && (
                  <circle key="pulse" r={r + 8} fill={color} fillOpacity={0.08} className="pulse-ring" />
                )}
                {isSelected && (
                  <circle key="select" r={r + 5} fill="none" stroke={color} strokeWidth={1.5} opacity={0.5} />
                )}
                <circle
                  key="main"
                  r={r}
                  fill={color}
                  fillOpacity={n.state === "offline" ? 0.2 : 0.85}
                  stroke={color}
                  strokeWidth={0.75}
                  style={isActive ? { filter: `drop-shadow(0 0 4px ${color}99)` } : undefined}
                  className={n.state === "encrypted" ? "node-blink" : undefined}
                />
                <text
                  key="label"
                  y={r + 9}
                  textAnchor="middle"
                  fill="#94A3B8"
                  fontSize={7}
                  fontFamily="JetBrains Mono, monospace"
                >
                  {n.name.length > 14 ? n.name.slice(0, 13) + "…" : n.name}
                </text>
              </g>
            );
          })}
        </svg>

        {graphNodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="text-xs font-mono text-text-muted">Start simulation to load topology</span>
          </div>
        )}
      </div>

      {/* Side panel */}
      <aside className="w-64 bg-bg-surface border-l border-bg-border flex flex-col overflow-hidden flex-shrink-0">
        <div className="px-3 py-2.5 border-b border-bg-border flex-shrink-0">
          <span className="text-2xs font-mono font-medium text-text-secondary uppercase tracking-widest">
            Node Inspector
          </span>
        </div>

        {selected ? (
          <NodeInspector node={selected} />
        ) : (
          <GraphStats nodes={graphNodes} />
        )}
      </aside>
    </div>
  );
}

function NodeInspector({ node }: { node: GraphNode }) {
  const color = NODE_STATE_COLORS[node.state] ?? "#7CFFB2";
  const loadPct = Math.round(node.load * 100);
  const liveNode = useGuardioStore((s) => s.nodes[node.id]);

  return (
    <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
      <div>
        <div className="text-sm font-medium text-text-primary">{liveNode?.name || node.name}</div>
        <div className="text-2xs font-mono text-text-muted mt-0.5 uppercase">
          {node.type} · {node.zone}
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="flex justify-between">
          <span className="text-2xs font-mono text-text-muted">STATE</span>
          <span className="text-2xs font-mono font-medium" style={{ color }}>
            {(liveNode?.state || node.state).toUpperCase()}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-2xs font-mono text-text-muted">LOAD</span>
          <div className="flex items-center gap-1.5">
            <div className="w-20 h-1 bg-bg-border rounded-full overflow-hidden">
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
        <div className="flex justify-between">
          <span className="text-2xs font-mono text-text-muted">ID</span>
          <span className="text-2xs font-mono text-text-dim">{node.id}</span>
        </div>
      </div>

      {liveNode?.services && liveNode.services.length > 0 && (
        <div>
          <div className="text-2xs font-mono text-text-muted mb-1.5">SERVICES</div>
          <div className="flex flex-wrap gap-1">
            {liveNode.services.map((s) => (
              <span key={s} className="px-1.5 py-0.5 text-2xs font-mono bg-bg-elevated border border-bg-border rounded text-text-secondary">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function GraphStats({ nodes }: { nodes: GraphNode[] }) {
  const byState: Record<string, number> = {};
  for (const n of nodes) {
    byState[n.state] = (byState[n.state] || 0) + 1;
  }

  const statOrder = ["healthy", "probing", "stressed", "compromised", "encrypted", "recovering", "offline"];

  return (
    <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
      <div>
        <div className="text-2xs font-mono text-text-muted mb-2">NODES BY STATE</div>
        <div className="space-y-1.5">
          {statOrder.filter((s) => byState[s]).map((state) => {
            const count = byState[state] || 0;
            const color = NODE_STATE_COLORS[state] ?? "#7CFFB2";
            const pct = nodes.length > 0 ? (count / nodes.length) * 100 : 0;
            return (
              <div key={state} className="flex items-center gap-2">
                <span className="w-16 text-2xs font-mono text-text-muted">{state}</span>
                <div className="flex-1 h-1 bg-bg-border rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
                </div>
                <span className="w-6 text-2xs font-mono text-text-secondary text-right tabular-nums">{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <div className="text-2xs font-mono text-text-muted mb-2">NODES BY TYPE</div>
        <div className="space-y-1">
          {["client", "server", "database", "cloud", "iot"].map((type) => {
            const count = nodes.filter((n) => n.type === type).length;
            return count > 0 ? (
              <div key={type} className="flex justify-between">
                <span className="text-2xs font-mono text-text-muted">{type}</span>
                <span className="text-2xs font-mono text-text-secondary tabular-nums">{count}</span>
              </div>
            ) : null;
          })}
        </div>
      </div>

      <div className="pt-1 border-t border-bg-border">
        <div className="flex justify-between">
          <span className="text-2xs font-mono text-text-muted">TOTAL</span>
          <span className="text-2xs font-mono text-text-primary tabular-nums">{nodes.length}</span>
        </div>
      </div>
    </div>
  );
}
