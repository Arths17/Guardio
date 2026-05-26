import asyncio
import random
from datetime import datetime
from typing import Optional, List
from .ws_manager import manager
from .replay import replays
from .defense import defense
from .ids import ids
from .db import db


class Simulation:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self.running = False
        self.active_attack: Optional[str] = None
        self._events: List[dict] = []

    async def _run(self):
        try:
            while self.running:
                # emit benign packet
                pkt = self._generate_packet(normal=True)
                # defense check
                if await defense.is_blocked(pkt["src"]) or await defense.is_blocked(pkt["dst"]):
                    drop = {"type": "dropped", "src": pkt["src"], "dst": pkt["dst"], "ts": datetime.utcnow().isoformat() + "Z"}
                    await manager.broadcast_json(drop)
                    self._events.append(drop)
                else:
                    await manager.broadcast_json(pkt)
                    self._events.append(pkt)

                alert = ids.alert_for(pkt)
                if alert:
                    await manager.broadcast_json(alert)
                    self._events.append(alert)

                # occasionally emit suspicious or malicious packets
                if random.random() < 0.05:
                    pkt = self._generate_packet(normal=False)
                    if await defense.is_blocked(pkt["src"]) or await defense.is_blocked(pkt["dst"]):
                        drop = {"type": "dropped", "src": pkt["src"], "dst": pkt["dst"], "ts": datetime.utcnow().isoformat() + "Z"}
                        await manager.broadcast_json(drop)
                        self._events.append(drop)
                    else:
                        await manager.broadcast_json(pkt)
                        self._events.append(pkt)
                        alert = ids.alert_for(pkt)
                        if alert:
                            await manager.broadcast_json(alert)
                            self._events.append(alert)

                await asyncio.sleep(0.15)
        except asyncio.CancelledError:
            return

    def _generate_packet(self, normal=True):
        now = datetime.utcnow().isoformat() + "Z"
        src = f"host-{random.randint(1,200)}"
        dst = f"srv-{random.randint(1,20)}"
        proto = random.choice(["tcp", "udp", "http"])
        if normal:
            color = "blue"
            size = random.randint(100, 1200)
        else:
            color = random.choice(["yellow", "red"])
            size = random.randint(1200, 10000)
        return {"type": "packet", "src": src, "dst": dst, "protocol": proto, "color": color, "size": size, "ts": now}

    async def start(self):
        if self.running:
            return
        self.running = True
        self._events = []
        # initial state broadcast
        await manager.broadcast_json({"type": "state", "running": True, "ts": datetime.utcnow().isoformat() + "Z"})
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        if not self.running:
            return
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await manager.broadcast_json({"type": "state", "running": False, "ts": datetime.utcnow().isoformat() + "Z"})
        # save replay
        rid = replays.save(self._events)
        try:
            db.save_replay(rid, self._events)
        except Exception:
            pass
        self._events = []
        return rid

    async def launch_attack(self, name: str):
        # simple attack simulation driver
        self.active_attack = name
        start = {"type": "attack", "name": name, "stage": "start", "details": {}, "ts": datetime.utcnow().isoformat() + "Z"}
        await manager.broadcast_json(start)
        self._events.append(start)

        if name == "ddos":
            # ramp up packet storm
            for i in range(60):
                pkt = self._generate_packet(normal=False)
                pkt["size"] = random.randint(2000, 15000)
                await manager.broadcast_json(pkt)
                self._events.append(pkt)
                await asyncio.sleep(0.02)

        elif name == "malware":
            # propagate infection events
            for i in range(30):
                now = datetime.utcnow().isoformat() + "Z"
                ev = {"type": "attack", "name": name, "stage": "update", "details": {"infected": f"host-{random.randint(1,200)}"}, "ts": now}
                await manager.broadcast_json(ev)
                self._events.append(ev)
                await asyncio.sleep(0.12)

        end = {"type": "attack", "name": name, "stage": "end", "details": {}, "ts": datetime.utcnow().isoformat() + "Z"}
        await manager.broadcast_json(end)
        self._events.append(end)
        self.active_attack = None


sim = Simulation()
