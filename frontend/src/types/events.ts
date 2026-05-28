export type NodeState =
  | "healthy"
  | "probing"
  | "stressed"
  | "compromised"
  | "encrypted"
  | "recovering"
  | "isolated"
  | "offline";

export type NodeType = "client" | "server" | "database" | "cloud" | "iot";
export type Zone = "external" | "dmz" | "internal" | "data" | "cloud" | "iot";

export type ThreatStatus = "LOW" | "GUARDED" | "ELEVATED" | "HIGH" | "CRITICAL";

export interface NodeData {
  id: string;
  name: string;
  type: NodeType;
  zone: Zone;
  lat: number;
  lng: number;
  services: string[];
  state: NodeState;
  load: number;
}

export interface PacketEvent {
  type: "packet";
  src: string;
  dst: string;
  src_lat: number;
  src_lng: number;
  dst_lat: number;
  dst_lng: number;
  src_zone: string;
  dst_zone: string;
  protocol: string;
  color: "blue" | "yellow" | "red" | "orange" | "purple" | "gray";
  size: number;
  flags: string;
  ttl: number;
  ts: string;
}

export interface AttackEvent {
  type: "attack";
  name: string;
  stage: "start" | "update" | "end";
  details: Record<string, unknown>;
  ts: string;
}

export interface NodeUpdateEvent {
  type: "node_update";
  node: string;
  name: string;
  state: NodeState;
  load: number;
  lat: number;
  lng: number;
  zone: string;
  ts: string;
}

export interface ThreatLevelEvent {
  type: "threat_level";
  level: number;
  delta: number;
  status: ThreatStatus;
  reason: string;
  ts: string;
}

export interface AlertEvent {
  type: "alert";
  alert_id: string;
  level: "medium" | "high" | "critical";
  score: number;
  reason: string;
  src: string;
  dst: string;
  protocol: string;
  src_lat: number;
  src_lng: number;
  dst_lat: number;
  dst_lng: number;
  ts: string;
}

export interface DefenseActionEvent {
  type: "defense_action";
  action: string;
  target?: string;
  details: Record<string, unknown>;
  color: string;
  ts: string;
}

export interface DroppedEvent {
  type: "dropped";
  src: string;
  dst: string;
  src_lat: number;
  src_lng: number;
  dst_lat: number;
  dst_lng: number;
  reason: string;
  color: string;
  ts: string;
}

export interface HoneypotEvent {
  type: "honeypot";
  src: string;
  dst: string;
  src_lat: number;
  src_lng: number;
  dst_lat: number;
  dst_lng: number;
  color: string;
  ts: string;
}

export interface InfraTelemetryEvent {
  type: "infra_telemetry";
  nodes: Array<{
    node: string;
    name: string;
    load: number;
    state: NodeState;
    lat: number;
    lng: number;
  }>;
  ts: string;
}

export interface StateEvent {
  type: "state";
  running?: boolean;
  simulation?: Record<string, unknown>;
  defense?: Record<string, unknown>;
  topology?: Record<string, NodeData>;
  threat_level?: number;
  threat_status?: ThreatStatus;
  clients?: number;
  ts: string;
}

export interface PingEvent {
  type: "ping" | "pong";
  ts: string;
}

export type GuardioEvent =
  | PacketEvent
  | AttackEvent
  | NodeUpdateEvent
  | ThreatLevelEvent
  | AlertEvent
  | DefenseActionEvent
  | DroppedEvent
  | HoneypotEvent
  | InfraTelemetryEvent
  | StateEvent
  | PingEvent;

export interface ArcDatum {
  id: string;
  srcLat: number;
  srcLng: number;
  dstLat: number;
  dstLng: number;
  color: string;
  protocol: string;
  ts: number;
}
