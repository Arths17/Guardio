from datetime import datetime
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class Attack(BaseModel):
    id: str
    name: str
    description: str
    severity: int
    tactics: List[str]
    techniques: List[str]


class Defense(BaseModel):
    id: str
    name: str
    description: str
    mitigates: List[str]


class SimulationResult(BaseModel):
    attack_id: str
    defense_id: str
    success: bool
    details: str


class PacketEvent(BaseModel):
    type: Literal["packet"] = "packet"
    src: str
    dst: str
    protocol: str
    color: Literal["blue", "yellow", "red", "green"]
    size: int
    ts: datetime


class AttackEvent(BaseModel):
    type: Literal["attack"] = "attack"
    name: str
    stage: Literal["start", "update", "end"]
    details: Dict[str, Any] = Field(default_factory=dict)
    ts: datetime


class SimulationState(BaseModel):
    running: bool
    active_attack: str | None = None
    clients: int = 0


class AttackRequest(BaseModel):
    name: Literal["ddos", "malware", "ransomware", "phishing", "botnet"]
    target: str | None = None
    intensity: int = Field(default=1, ge=1, le=10)


class HostActionRequest(BaseModel):
    host: str


class SegmentRequest(BaseModel):
    name: str
    hosts: List[str]


class ReplaySummary(BaseModel):
    id: str
    event_count: int


class MetricSnapshot(BaseModel):
    counts: Dict[str, int]
    last_event: Dict[str, Any] | None = None


class PhishingScoreRequest(BaseModel):
    url: str | None = None
    features: Dict[str, float] = Field(default_factory=dict)
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class PhishingScoreResponse(BaseModel):
    prediction: int
    probability: float
    threshold: float
    model_name: str
    source: Literal["url_heuristic", "feature_vector"]
    missing_features: List[str] = Field(default_factory=list)
    extra_features: List[str] = Field(default_factory=list)
