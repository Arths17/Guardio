import { create } from "zustand";
import type {
  NodeData,
  AlertEvent,
  AttackEvent,
  ArcDatum,
  ThreatStatus,
  PacketEvent,
  DefenseActionEvent,
} from "@/types/events";

const MAX_EVENTS = 200;
const MAX_ARCS = 60;
const MAX_ALERTS = 100;
const MAX_ATTACK_LOG = 80;

export interface ProtocolStat {
  protocol: string;
  count: number;
}

export interface IncidentEntry {
  id: string;
  ts: string;
  type: string;
  severity: "low" | "medium" | "high" | "critical";
  title: string;
  detail: string;
  raw: Record<string, unknown>;
}

interface GuardioState {
  connected: boolean;
  running: boolean;
  activeAttack: string | null;
  clientCount: number;

  threatLevel: number;
  threatStatus: ThreatStatus;

  nodes: Record<string, NodeData>;

  // Live arcs for the map
  arcs: ArcDatum[];

  // Alert feed
  alerts: AlertEvent[];

  // Attack log for timeline
  attackLog: AttackEvent[];

  // Unified incident feed
  incidents: IncidentEntry[];

  // Defense actions
  defenseActions: DefenseActionEvent[];

  // Counters
  packetCount: number;
  attackCount: number;
  alertCount: number;
  droppedCount: number;
  bytesTransferred: number;

  // Protocol breakdown
  protocolStats: Record<string, number>;

  // Recent packets for intel panel
  recentPackets: PacketEvent[];

  // AI suggestions
  aiSuggestions: Array<{ id: string; ts: string; text: string; action?: string }>;

  // Actions
  setConnected: (v: boolean) => void;
  setRunning: (v: boolean) => void;
  setTopology: (nodes: Record<string, NodeData>) => void;
  updateNode: (id: string, update: Partial<NodeData>) => void;
  setThreatLevel: (level: number, status: ThreatStatus) => void;
  addArc: (arc: ArcDatum) => void;
  addAlert: (alert: AlertEvent) => void;
  addAttackEvent: (ev: AttackEvent) => void;
  addDefenseAction: (ev: DefenseActionEvent) => void;
  addIncident: (inc: IncidentEntry) => void;
  addPacket: (pkt: PacketEvent) => void;
  incrementDropped: () => void;
  addAISuggestion: (text: string, action?: string) => void;
  setClientCount: (n: number) => void;
  reset: () => void;
}

function makeIncidentId() {
  return Math.random().toString(36).slice(2, 10);
}

export const useGuardioStore = create<GuardioState>((set) => ({
  connected: false,
  running: false,
  activeAttack: null,
  clientCount: 0,

  threatLevel: 0,
  threatStatus: "LOW",

  nodes: {},
  arcs: [],
  alerts: [],
  attackLog: [],
  incidents: [],
  defenseActions: [],
  recentPackets: [],
  aiSuggestions: [],

  packetCount: 0,
  attackCount: 0,
  alertCount: 0,
  droppedCount: 0,
  bytesTransferred: 0,
  protocolStats: {},

  setConnected: (v) => set({ connected: v }),
  setRunning: (v) => set({ running: v }),

  setTopology: (nodes) => set({ nodes }),

  updateNode: (id, update) =>
    set((s) => ({
      nodes: {
        ...s.nodes,
        [id]: s.nodes[id] ? { ...s.nodes[id], ...update } : (update as NodeData),
      },
    })),

  setThreatLevel: (level, status) => set({ threatLevel: level, threatStatus: status }),

  addArc: (arc) =>
    set((s) => {
      const arcs = [arc, ...s.arcs].slice(0, MAX_ARCS);
      return { arcs };
    }),

  addAlert: (alert) =>
    set((s) => ({
      alerts: [alert, ...s.alerts].slice(0, MAX_ALERTS),
      alertCount: s.alertCount + 1,
    })),

  addAttackEvent: (ev) =>
    set((s) => ({
      attackLog: [ev, ...s.attackLog].slice(0, MAX_ATTACK_LOG),
      activeAttack: ev.stage !== "end" ? ev.name : null,
      attackCount: ev.stage === "start" ? s.attackCount + 1 : s.attackCount,
    })),

  addDefenseAction: (ev) =>
    set((s) => ({
      defenseActions: [ev, ...s.defenseActions].slice(0, 50),
    })),

  addIncident: (inc) =>
    set((s) => ({
      incidents: [inc, ...s.incidents].slice(0, MAX_EVENTS),
    })),

  addPacket: (pkt) =>
    set((s) => {
      const proto = pkt.protocol || "unknown";
      return {
        packetCount: s.packetCount + 1,
        bytesTransferred: s.bytesTransferred + pkt.size,
        protocolStats: {
          ...s.protocolStats,
          [proto]: (s.protocolStats[proto] || 0) + 1,
        },
        recentPackets: [pkt, ...s.recentPackets].slice(0, 200),
      };
    }),

  incrementDropped: () => set((s) => ({ droppedCount: s.droppedCount + 1 })),

  addAISuggestion: (text, action) =>
    set((s) => ({
      aiSuggestions: [
        { id: makeIncidentId(), ts: new Date().toISOString(), text, action },
        ...s.aiSuggestions,
      ].slice(0, 20),
    })),

  setClientCount: (n) => set({ clientCount: n }),

  reset: () =>
    set({
      running: false,
      activeAttack: null,
      threatLevel: 0,
      threatStatus: "LOW",
      nodes: {},
      arcs: [],
      alerts: [],
      attackLog: [],
      incidents: [],
      defenseActions: [],
      recentPackets: [],
      packetCount: 0,
      attackCount: 0,
      alertCount: 0,
      droppedCount: 0,
      bytesTransferred: 0,
      protocolStats: {},
    }),
}));
