import asyncio
from backend.lifecycle import create_task
import random
from typing import Any, Dict, List, Optional

from backend.defense import defense
from backend.ids import ids
from backend.telemetry import telemetry
from backend.replay import replays
from backend.utils import utc_now_iso
from backend.ws_manager import manager


class Simulation:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self.running: bool = False
        self.active_attack: Optional[str] = None
        self._events: List[dict] = []
        self._compromised_hosts: set[str] = set()
        self._attack_lock = asyncio.Lock()
        self.topology: Dict[str, List[str]] = {
            "clients": [f"host-{i}" for i in range(1, 81)],
            "servers": [f"srv-{i}" for i in range(1, 13)],
            "databases": ["db-1", "db-2"],
            "cloud": ["cloud-1", "cloud-2"],
            "iot": [f"iot-{i}" for i in range(1, 13)],
        }

    def _pick(self, pool: str) -> str:
        return random.choice(self.topology[pool])

    def _target_host(self) -> str:
        return random.choice(self.topology["servers"] + self.topology["databases"])

    def _generate_packet(
        self,
        normal: bool = True,
        src: Optional[str] = None,
        dst: Optional[str] = None,
    ) -> dict:
        packet = {
            "type": "packet",
            "src": src or self._pick("clients"),
            "dst": dst or self._target_host(),
            "protocol": random.choice(["tcp", "udp", "http", "tls"]),
            "color": "blue" if normal else random.choice(["yellow", "red"]),
            "size": (
                random.randint(100, 1200) if normal else random.randint(1200, 10000)
            ),
            "ts": utc_now_iso(),
        }
        return packet

    async def _record_event(self, event: dict) -> None:
        await manager.broadcast_json(event)
        self._events.append(event)
        telemetry.increment("simulation_events")

    async def _emit_packet(self, packet: dict) -> None:
        if await defense.is_blocked(packet["src"]) or await defense.is_blocked(
            packet["dst"]
        ):
            dropped = {
                "type": "dropped",
                "src": packet["src"],
                "dst": packet["dst"],
                "reason": "firewall",
                "ts": utc_now_iso(),
            }
            await self._record_event(dropped)
            return

        src_segment = await defense.segment_for(packet["src"])
        dst_segment = await defense.segment_for(packet["dst"])
        if src_segment and dst_segment and src_segment != dst_segment:
            dropped = {
                "type": "dropped",
                "src": packet["src"],
                "dst": packet["dst"],
                "reason": "segment-isolation",
                "ts": utc_now_iso(),
            }
            await self._record_event(dropped)
            return

        if await defense.is_honeypot(packet["dst"]):
            honeypot_hit = {
                "type": "honeypot",
                "src": packet["src"],
                "dst": packet["dst"],
                "ts": utc_now_iso(),
            }
            await self._record_event(honeypot_hit)

        await self._record_event(packet)
        alert = ids.alert_for(packet)
        if alert:
            await self._record_event(alert)

    async def _run(self) -> None:
        try:
            while self.running:
                await self._emit_packet(self._generate_packet(normal=True))

                if random.random() < 0.10:
                    await self._emit_packet(self._generate_packet(normal=False))

                if self._compromised_hosts and random.random() < 0.15:
                    infected_src = random.choice(sorted(self._compromised_hosts))
                    await self._emit_packet(
                        self._generate_packet(normal=False, src=infected_src)
                    )

                await asyncio.sleep(0.15)
        except asyncio.CancelledError:
            return

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.active_attack = "monitoring"
        self._events = []
        telemetry.increment("simulation_starts")
        await manager.broadcast_json(
            {"type": "state", "running": True, "ts": utc_now_iso()}
        )
        self._task = create_task(self._run())

    async def stop(self) -> Optional[str]:
        if not self.running:
            return None
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await manager.broadcast_json(
            {"type": "state", "running": False, "ts": utc_now_iso()}
        )
        rid = replays.save(self._events)
        self._events = []
        self._compromised_hosts.clear()
        self.active_attack = None
        telemetry.increment("simulation_stops")
        return rid

    async def launch_attack(self, name: str) -> None:
        async with self._attack_lock:
            if self.active_attack and self.active_attack != name:
                return
            self.active_attack = name

        telemetry.increment(f"attack_{name}_starts")
        start_event = {
            "type": "attack",
            "name": name,
            "stage": "start",
            "details": {},
            "ts": utc_now_iso(),
        }
        await self._record_event(start_event)

        handlers = {
            "ddos": self._attack_ddos,
            "malware": self._attack_malware,
            "ransomware": self._attack_ransomware,
            "phishing": self._attack_phishing,
            "botnet": self._attack_botnet,
        }
        handler = handlers.get(name)
        if handler is not None:
            await handler()
        else:
            await self._record_event(
                {
                    "type": "attack",
                    "name": name,
                    "stage": "update",
                    "details": {"status": "unknown-attack"},
                    "ts": utc_now_iso(),
                }
            )

        end_event = {
            "type": "attack",
            "name": name,
            "stage": "end",
            "details": {},
            "ts": utc_now_iso(),
        }
        await self._record_event(end_event)
        telemetry.increment(f"attack_{name}_ends")

        async with self._attack_lock:
            self.active_attack = None

    async def _attack_ddos(self) -> None:
        target = self._target_host()
        for _ in range(80):
            packet = self._generate_packet(normal=False, dst=target)
            packet["color"] = "red"
            packet["size"] = random.randint(4000, 16000)
            await self._emit_packet(packet)
            telemetry.increment("bandwidth_spikes")
            await asyncio.sleep(0.015)

    async def _attack_malware(self) -> None:
        victim = self._pick("clients")
        self._compromised_hosts.add(victim)
        for hop in range(24):
            new_victim = self._pick("clients")
            self._compromised_hosts.add(new_victim)
            event = {
                "type": "attack",
                "name": "malware",
                "stage": "update",
                "details": {
                    "infected": new_victim,
                    "from": victim,
                    "hop": hop,
                },
                "ts": utc_now_iso(),
            }
            await self._record_event(event)
            await self._emit_packet(
                self._generate_packet(normal=False, src=victim, dst=new_victim)
            )
            victim = new_victim
            await asyncio.sleep(0.08)

    async def _attack_ransomware(self) -> None:
        targets = random.sample(
            self.topology["servers"] + self.topology["databases"], 4
        )
        for target in targets:
            event = {
                "type": "attack",
                "name": "ransomware",
                "stage": "update",
                "details": {"locked": target, "state": "encrypted"},
                "ts": utc_now_iso(),
            }
            await self._record_event(event)
            await self._emit_packet(self._generate_packet(normal=False, dst=target))

    async def _attack_phishing(self) -> None:
        for _ in range(18):
            victim = self._pick("clients")
            event = {
                "type": "attack",
                "name": "phishing",
                "stage": "update",
                "details": {
                    "victim": victim,
                    "credential_theft": bool(random.getrandbits(1)),
                },
                "ts": utc_now_iso(),
            }
            await self._record_event(event)
            await self._emit_packet(
                self._generate_packet(normal=False, src="phisher", dst=victim)
            )
            await asyncio.sleep(0.05)

    async def _attack_botnet(self) -> None:
        command_host = self._pick("cloud")
        bots = random.sample(self.topology["iot"] + self.topology["clients"], 8)
        for bot in bots:
            self._compromised_hosts.add(bot)
            event = {
                "type": "attack",
                "name": "botnet",
                "stage": "update",
                "details": {"bot": bot, "controller": command_host},
                "ts": utc_now_iso(),
            }
            await self._record_event(event)
            await self._emit_packet(
                self._generate_packet(normal=False, src=bot, dst=command_host)
            )
            await asyncio.sleep(0.04)

    def snapshot(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "active_attack": self.active_attack,
            "events": len(self._events),
            "compromised_hosts": len(self._compromised_hosts),
        }


sim = Simulation()
