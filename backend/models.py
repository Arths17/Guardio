from pydantic import BaseModel
from typing import Literal, Any, Dict
from datetime import datetime


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
    details: Dict[str, Any] = {}
    ts: datetime


class SimulationState(BaseModel):
    running: bool
    active_attack: str | None = None
    clients: int = 0
