from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class NodeType(str, Enum):
    CLIENT = "client"
    SERVER = "server"
    DATABASE = "database"
    CLOUD = "cloud"
    IOT = "iot"


class Zone(str, Enum):
    EXTERNAL = "external"
    DMZ = "dmz"
    INTERNAL = "internal"
    DATA = "data"
    CLOUD = "cloud"
    IOT = "iot"


class NodeState(str, Enum):
    HEALTHY = "healthy"
    PROBING = "probing"
    STRESSED = "stressed"
    COMPROMISED = "compromised"
    ENCRYPTED = "encrypted"
    RECOVERING = "recovering"
    ISOLATED = "isolated"
    OFFLINE = "offline"


@dataclass
class Node:
    id: str
    name: str
    type: NodeType
    zone: Zone
    lat: float
    lng: float
    services: List[str] = field(default_factory=list)
    state: NodeState = NodeState.HEALTHY
    load: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "zone": self.zone.value,
            "lat": self.lat,
            "lng": self.lng,
            "services": self.services,
            "state": self.state.value,
            "load": round(self.load, 3),
        }


def _build_topology() -> Dict[str, Node]:
    nodes: Dict[str, Node] = {}
    rng = random.Random(42)  # deterministic seed for reproducible topology

    # 30 named client locations with real-world coordinates
    _named_clients = [
        ("host-1",  "Workstation-SF",      37.77, -122.42),
        ("host-2",  "Workstation-NY",      40.71,  -74.01),
        ("host-3",  "Workstation-London",  51.51,   -0.13),
        ("host-4",  "Workstation-Paris",   48.85,    2.35),
        ("host-5",  "Workstation-Berlin",  52.52,   13.41),
        ("host-6",  "Workstation-Tokyo",   35.68,  139.69),
        ("host-7",  "Workstation-Beijing", 39.91,  116.39),
        ("host-8",  "Workstation-Mumbai",  19.07,   72.88),
        ("host-9",  "Workstation-Sao",    -23.55,  -46.63),
        ("host-10", "Workstation-Sydney", -33.87,  151.21),
        ("host-11", "Workstation-Moscow",  55.75,   37.62),
        ("host-12", "Workstation-SG",       1.35,  103.82),
        ("host-13", "Workstation-Dubai",   25.20,   55.27),
        ("host-14", "Workstation-Toronto", 43.65,  -79.38),
        ("host-15", "Workstation-LA",      34.05, -118.24),
        ("host-16", "Workstation-Seattle", 47.61, -122.33),
        ("host-17", "Workstation-Chicago", 41.88,  -87.63),
        ("host-18", "Workstation-Houston", 29.76,  -95.37),
        ("host-19", "Workstation-Phoenix", 33.45, -112.07),
        ("host-20", "Workstation-Boston",  42.36,  -71.06),
        ("host-21", "Workstation-Rome",    41.90,   12.50),
        ("host-22", "Workstation-Madrid",  40.42,   -3.70),
        ("host-23", "Workstation-Brussels",50.85,    4.35),
        ("host-24", "Workstation-Stockholm",59.33,  18.07),
        ("host-25", "Workstation-Helsinki",60.17,   24.94),
        ("host-26", "Workstation-Seoul",   37.57,  126.98),
        ("host-27", "Workstation-HongKong",22.28,  114.16),
        ("host-28", "Workstation-Bangkok", 13.75,  100.52),
        ("host-29", "Workstation-Jakarta", -6.21,  106.85),
        ("host-30", "Workstation-KL",       3.14,  101.69),
    ]

    for nid, name, lat, lng in _named_clients:
        nodes[nid] = Node(
            id=nid, name=name,
            type=NodeType.CLIENT, zone=Zone.EXTERNAL,
            lat=lat + rng.uniform(-0.3, 0.3),
            lng=lng + rng.uniform(-0.3, 0.3),
            services=["http", "dns", "tls"],
        )

    # Fill remaining 50 clients with scattered coordinates
    for i in range(31, 81):
        nid = f"host-{i}"
        lat = rng.uniform(-55, 70)
        lng = rng.uniform(-170, 170)
        nodes[nid] = Node(
            id=nid, name=f"Endpoint-{i:02d}",
            type=NodeType.CLIENT, zone=Zone.EXTERNAL,
            lat=lat, lng=lng,
            services=["http", "dns"],
        )

    # Server nodes — Silicon Valley datacenter cluster
    _server_configs = [
        ("srv-1",  "Web-Nginx-01",     37.3382, -121.8863, ["http", "https", "nginx"]),
        ("srv-2",  "Web-Nginx-02",     37.3384, -121.8860, ["http", "https", "nginx"]),
        ("srv-3",  "API-Gateway-01",   37.3388, -121.8858, ["http", "grpc", "rest"]),
        ("srv-4",  "API-Gateway-02",   37.3390, -121.8855, ["http", "grpc", "rest"]),
        ("srv-5",  "Auth-Server",      37.3386, -121.8870, ["https", "oauth2", "jwt"]),
        ("srv-6",  "Cache-Redis",      37.3392, -121.8868, ["redis", "tcp"]),
        ("srv-7",  "Mail-Server",      37.3394, -121.8865, ["smtp", "imap", "pop3"]),
        ("srv-8",  "DNS-Resolver",     37.3396, -121.8862, ["dns", "tcp", "udp"]),
        ("srv-9",  "Load-Balancer",    37.3380, -121.8845, ["tcp", "http", "tls"]),
        ("srv-10", "Monitoring",       37.3382, -121.8843, ["prometheus", "http"]),
        ("srv-11", "CI-CD",            37.3376, -121.8850, ["git", "docker", "http"]),
        ("srv-12", "Backup-Server",    37.3374, -121.8847, ["rsync", "sftp", "s3"]),
    ]

    for sid, name, lat, lng, services in _server_configs:
        nodes[sid] = Node(
            id=sid, name=name,
            type=NodeType.SERVER, zone=Zone.DMZ,
            lat=lat, lng=lng, services=services,
        )

    # Database nodes — air-gapped data zone
    nodes["db-1"] = Node(
        id="db-1", name="Primary-PostgreSQL",
        type=NodeType.DATABASE, zone=Zone.DATA,
        lat=37.3370, lng=-121.8890,
        services=["postgresql", "ssl", "replication"],
    )
    nodes["db-2"] = Node(
        id="db-2", name="Replica-PostgreSQL",
        type=NodeType.DATABASE, zone=Zone.DATA,
        lat=37.3368, lng=-121.8887,
        services=["postgresql", "replication"],
    )

    # Cloud nodes — geographically distributed
    nodes["cloud-1"] = Node(
        id="cloud-1", name="AWS-us-east-1",
        type=NodeType.CLOUD, zone=Zone.CLOUD,
        lat=39.04, lng=-77.49,
        services=["s3", "ec2", "rds", "lambda", "cloudfront"],
    )
    nodes["cloud-2"] = Node(
        id="cloud-2", name="GCP-us-west1",
        type=NodeType.CLOUD, zone=Zone.CLOUD,
        lat=37.42, lng=-122.08,
        services=["gcs", "gke", "bigquery", "pubsub"],
    )

    # IoT nodes — physical facility
    _iot_configs = [
        ("iot-1",  "Security-Cam-01",    37.3350, -121.8820, ["rtsp", "mqtt"]),
        ("iot-2",  "Security-Cam-02",    37.3352, -121.8818, ["rtsp", "mqtt"]),
        ("iot-3",  "HVAC-Controller",    37.3354, -121.8816, ["modbus", "mqtt"]),
        ("iot-4",  "Access-Control",     37.3356, -121.8814, ["wiegand", "tcp"]),
        ("iot-5",  "Industrial-PLC",     37.3358, -121.8812, ["modbus", "opc-ua"]),
        ("iot-6",  "Smart-Meter",        37.3360, -121.8810, ["dlms", "mqtt"]),
        ("iot-7",  "Network-Printer",    37.3362, -121.8808, ["ipp", "tcp"]),
        ("iot-8",  "VoIP-Gateway",       37.3364, -121.8806, ["sip", "rtp"]),
        ("iot-9",  "Badge-Reader",       37.3366, -121.8804, ["wiegand", "tcp"]),
        ("iot-10", "Temp-Sensor",        37.3368, -121.8802, ["coap", "mqtt"]),
        ("iot-11", "Fire-Alarm-Hub",     37.3370, -121.8800, ["bacnet", "tcp"]),
        ("iot-12", "Elevator-Control",   37.3372, -121.8798, ["bacnet", "modbus"]),
    ]

    for nid, name, lat, lng, services in _iot_configs:
        nodes[nid] = Node(
            id=nid, name=name,
            type=NodeType.IOT, zone=Zone.IOT,
            lat=lat, lng=lng, services=services,
        )

    return nodes


NODES: Dict[str, Node] = _build_topology()


def pool_of(node_type: NodeType) -> List[str]:
    return [nid for nid, n in NODES.items() if n.type == node_type]
