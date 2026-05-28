from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List, Optional

from backend.lifecycle import create_task
from backend.defense import defense
from backend.ids import ids
from backend.telemetry import telemetry
from backend.replay import replays
from backend.utils import utc_now_iso
from backend.ws_manager import manager
from backend.topology import NODES, NodeState, NodeType, pool_of

_PROTOCOLS_NORMAL = ["TCP", "UDP", "HTTP/1.1", "HTTPS", "TLS/1.3", "DNS", "NTP", "SMTP"]
_PROTOCOLS_ATTACK = ["TCP-SYN", "UDP-FLOOD", "ICMP-FLOOD", "NTP-AMP", "HTTP-POST", "SMB", "RDP"]

_THREAT_WEIGHTS: Dict[str, float] = {
    "ddos": 2.0,
    "malware": 3.5,
    "ransomware": 5.0,
    "phishing": 1.5,
    "botnet": 2.5,
    "apt": 4.0,
}


class Simulation:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self.running: bool = False
        self.active_attack: Optional[str] = None
        self._events: List[dict] = []
        self._compromised_hosts: set[str] = set()
        self._attack_lock = asyncio.Lock()
        self._threat_level: float = 0.0

        self.topology: Dict[str, List[str]] = {
            "clients":   pool_of(NodeType.CLIENT),
            "servers":   pool_of(NodeType.SERVER),
            "databases": pool_of(NodeType.DATABASE),
            "cloud":     pool_of(NodeType.CLOUD),
            "iot":       pool_of(NodeType.IOT),
        }

    # ── helpers ───────────────────────────────────────────────────────────────

    def _pick(self, pool: str) -> str:
        return random.choice(self.topology[pool])

    def _target_host(self) -> str:
        return random.choice(self.topology["servers"] + self.topology["databases"])

    def _node_meta(self, node_id: str) -> dict:
        node = NODES.get(node_id)
        if node is None:
            return {"lat": 0.0, "lng": 0.0, "zone": "unknown", "name": node_id}
        return {
            "lat": node.lat,
            "lng": node.lng,
            "zone": node.zone.value,
            "name": node.name,
        }

    def _generate_packet(
        self,
        normal: bool = True,
        src: Optional[str] = None,
        dst: Optional[str] = None,
        protocol: Optional[str] = None,
        override_src_lat: Optional[float] = None,
        override_src_lng: Optional[float] = None,
    ) -> dict:
        src_id = src or self._pick("clients")
        dst_id = dst or self._target_host()
        src_meta = self._node_meta(src_id)
        dst_meta = self._node_meta(dst_id)

        return {
            "type": "packet",
            "src": src_id,
            "dst": dst_id,
            "src_lat": override_src_lat if override_src_lat is not None else src_meta["lat"],
            "src_lng": override_src_lng if override_src_lng is not None else src_meta["lng"],
            "dst_lat": dst_meta["lat"],
            "dst_lng": dst_meta["lng"],
            "src_zone": src_meta["zone"],
            "dst_zone": dst_meta["zone"],
            "protocol": protocol or (
                random.choice(_PROTOCOLS_NORMAL) if normal
                else random.choice(_PROTOCOLS_ATTACK)
            ),
            "color": "blue" if normal else random.choice(["yellow", "red", "orange"]),
            "size": (
                random.randint(64, 1500) if normal else random.randint(1500, 65535)
            ),
            "flags": "ACK" if normal else random.choice(["SYN", "SYN-ACK", "RST", "PSH-ACK"]),
            "ttl": random.randint(55, 128) if normal else random.randint(1, 64),
            "ts": utc_now_iso(),
        }

    async def _set_node_state(
        self,
        node_id: str,
        state: NodeState,
        load: Optional[float] = None,
    ) -> None:
        node = NODES.get(node_id)
        if node is None:
            return
        node.state = state
        if load is not None:
            node.load = max(0.0, min(1.0, load))
        await self._record_event({
            "type": "node_update",
            "node": node_id,
            "name": node.name,
            "state": state.value,
            "load": round(node.load, 3),
            "lat": node.lat,
            "lng": node.lng,
            "zone": node.zone.value,
            "ts": utc_now_iso(),
        })

    async def _update_threat(self, delta: float, reason: str = "") -> None:
        self._threat_level = max(0.0, min(100.0, self._threat_level + delta))
        await self._record_event({
            "type": "threat_level",
            "level": round(self._threat_level, 1),
            "delta": round(delta, 1),
            "status": self._threat_status(),
            "reason": reason,
            "ts": utc_now_iso(),
        })

    def _threat_status(self) -> str:
        lvl = self._threat_level
        if lvl >= 80:
            return "CRITICAL"
        if lvl >= 60:
            return "HIGH"
        if lvl >= 40:
            return "ELEVATED"
        if lvl >= 20:
            return "GUARDED"
        return "LOW"

    async def _record_event(self, event: dict) -> None:
        await manager.broadcast_json(event)
        self._events.append(event)
        telemetry.increment("simulation_events")

    async def _emit_packet(self, packet: dict) -> None:
        src, dst = packet["src"], packet["dst"]

        if await defense.is_blocked(src) or await defense.is_blocked(dst):
            await self._record_event({
                "type": "dropped",
                "src": src, "dst": dst,
                "src_lat": packet.get("src_lat", 0),
                "src_lng": packet.get("src_lng", 0),
                "dst_lat": packet.get("dst_lat", 0),
                "dst_lng": packet.get("dst_lng", 0),
                "reason": "firewall",
                "color": "gray",
                "ts": utc_now_iso(),
            })
            return

        src_seg = await defense.segment_for(src)
        dst_seg = await defense.segment_for(dst)
        if src_seg and dst_seg and src_seg != dst_seg:
            await self._record_event({
                "type": "dropped",
                "src": src, "dst": dst,
                "src_lat": packet.get("src_lat", 0),
                "src_lng": packet.get("src_lng", 0),
                "dst_lat": packet.get("dst_lat", 0),
                "dst_lng": packet.get("dst_lng", 0),
                "reason": "segment-isolation",
                "color": "gray",
                "ts": utc_now_iso(),
            })
            return

        if await defense.is_honeypot(dst):
            await self._record_event({
                "type": "honeypot",
                "src": src, "dst": dst,
                "src_lat": packet.get("src_lat", 0),
                "src_lng": packet.get("src_lng", 0),
                "dst_lat": packet.get("dst_lat", 0),
                "dst_lng": packet.get("dst_lng", 0),
                "color": "purple",
                "ts": utc_now_iso(),
            })
            await self._update_threat(5.0, f"honeypot triggered by {src}")

        await self._record_event(packet)
        alert = ids.alert_for(packet)
        if alert:
            await self._record_event(alert)
            await self._update_threat(2.0, alert.get("reason", "anomaly"))

    # ── background loop ───────────────────────────────────────────────────────

    async def _run(self) -> None:
        tick = 0
        try:
            while self.running:
                await self._emit_packet(self._generate_packet(normal=True))

                if random.random() < 0.10:
                    await self._emit_packet(self._generate_packet(normal=False))

                # Compromised hosts beacon to C2
                if self._compromised_hosts and random.random() < 0.20:
                    src = random.choice(list(self._compromised_hosts))
                    c2 = self._pick("cloud")
                    await self._emit_packet(
                        self._generate_packet(
                            normal=False, src=src, dst=c2, protocol="HTTPS",
                        )
                    )

                if tick % 20 == 0 and self._threat_level > 0:
                    await self._update_threat(-1.0, "decay")

                if tick % 10 == 0:
                    await self._emit_infra_telemetry()

                tick += 1
                await asyncio.sleep(0.12)
        except asyncio.CancelledError:
            return

    async def _emit_infra_telemetry(self) -> None:
        candidates = self.topology["servers"] + self.topology["databases"]
        sampled = random.sample(candidates, min(4, len(candidates)))
        metrics = []
        for nid in sampled:
            node = NODES.get(nid)
            if node is None:
                continue
            base = 0.3 if node.state == NodeState.HEALTHY else 0.8
            if nid in self._compromised_hosts:
                base = 0.95
            node.load = max(0.0, min(1.0, base + random.uniform(-0.08, 0.12)))
            metrics.append({
                "node": nid,
                "name": node.name,
                "load": round(node.load, 3),
                "state": node.state.value,
                "lat": node.lat,
                "lng": node.lng,
            })
        if metrics:
            await self._record_event({
                "type": "infra_telemetry",
                "nodes": metrics,
                "ts": utc_now_iso(),
            })

    # ── lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.active_attack = "monitoring"
        self._events = []
        self._threat_level = 5.0

        for node in NODES.values():
            node.state = NodeState.HEALTHY
            node.load = random.uniform(0.1, 0.4)

        telemetry.increment("simulation_starts")
        await manager.broadcast_json({
            "type": "state",
            "running": True,
            "topology": {nid: n.to_dict() for nid, n in NODES.items()},
            "threat_level": self._threat_level,
            "threat_status": self._threat_status(),
            "ts": utc_now_iso(),
        })
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

        await manager.broadcast_json({"type": "state", "running": False, "ts": utc_now_iso()})
        rid = replays.save(self._events)
        self._events = []
        self._compromised_hosts.clear()
        self.active_attack = None
        self._threat_level = 0.0
        for node in NODES.values():
            node.state = NodeState.HEALTHY
            node.load = 0.0
        ids.reset_rates()
        telemetry.increment("simulation_stops")
        return rid

    # ── attack dispatcher ─────────────────────────────────────────────────────

    async def launch_attack(self, name: str) -> None:
        async with self._attack_lock:
            if self.active_attack and self.active_attack != name:
                return
            self.active_attack = name

        telemetry.increment(f"attack_{name}_starts")
        await self._record_event({
            "type": "attack",
            "name": name,
            "stage": "start",
            "details": {
                "phase": "initializing",
                "threat_level": round(self._threat_level, 1),
            },
            "ts": utc_now_iso(),
        })
        await self._update_threat(
            _THREAT_WEIGHTS.get(name, 2.0) * 2,
            f"{name} attack initiated",
        )

        handlers = {
            "ddos":       self._attack_ddos,
            "malware":    self._attack_malware,
            "ransomware": self._attack_ransomware,
            "phishing":   self._attack_phishing,
            "botnet":     self._attack_botnet,
            "apt":        self._attack_apt,
        }
        handler = handlers.get(name)
        if handler is not None:
            await handler()
        else:
            await self._record_event({
                "type": "attack", "name": name, "stage": "update",
                "details": {"status": "unknown-attack"},
                "ts": utc_now_iso(),
            })

        await self._record_event({
            "type": "attack", "name": name, "stage": "end",
            "details": {"events_generated": len(self._events)},
            "ts": utc_now_iso(),
        })
        telemetry.increment(f"attack_{name}_ends")
        async with self._attack_lock:
            self.active_attack = None

    # ── attack engines ────────────────────────────────────────────────────────

    async def _attack_ddos(self) -> None:
        target = self._pick("servers")
        meta = self._node_meta(target)

        # Phase 1 — probe
        await self._record_event({
            "type": "attack", "name": "ddos", "stage": "update",
            "details": {
                "phase": "probe",
                "target": target, "target_lat": meta["lat"], "target_lng": meta["lng"],
                "message": f"Reconnaissance of {meta['name']}",
            },
            "ts": utc_now_iso(),
        })
        await self._set_node_state(target, NodeState.PROBING, 0.4)
        for _ in range(10):
            p = self._generate_packet(normal=False, dst=target, protocol="ICMP")
            p.update({"color": "yellow", "size": random.randint(64, 256)})
            await self._emit_packet(p)
            await asyncio.sleep(0.03)

        # Phase 2 — volumetric flood
        attackers = random.sample(
            self.topology["clients"] + self.topology["iot"],
            min(20, len(self.topology["clients"]) + len(self.topology["iot"])),
        )
        await self._record_event({
            "type": "attack", "name": "ddos", "stage": "update",
            "details": {
                "phase": "flood",
                "target": target, "attacker_count": len(attackers),
                "message": f"Volumetric flood on {meta['name']} from {len(attackers)} sources",
                "pps_estimate": 45000,
            },
            "ts": utc_now_iso(),
        })
        await self._set_node_state(target, NodeState.STRESSED, 0.85)
        await self._update_threat(10.0, "DDoS flood phase")

        for wave in range(4):
            for attacker in attackers:
                p = self._generate_packet(
                    normal=False, src=attacker, dst=target, protocol="UDP-FLOOD",
                )
                p.update({"color": "red", "size": random.randint(1400, 65535)})
                await self._emit_packet(p)
            telemetry.increment("bandwidth_spikes")
            await self._update_threat(5.0, f"DDoS wave {wave + 1}")
            await asyncio.sleep(0.04)

        # Phase 3 — saturation
        await self._record_event({
            "type": "attack", "name": "ddos", "stage": "update",
            "details": {
                "phase": "saturated",
                "target": target,
                "message": f"⚠️  {meta['name']} is DOWN — availability 0%",
                "availability": 0,
            },
            "ts": utc_now_iso(),
        })
        await self._set_node_state(target, NodeState.OFFLINE, 1.0)
        await self._update_threat(15.0, "target offline")
        await asyncio.sleep(0.25)

        # Automated defense response
        await self._record_event({
            "type": "defense_action",
            "action": "rate_limiting",
            "target": target,
            "details": {
                "message": "Anycast scrubbing activated — redirecting traffic to cleaning center",
                "blocked_sources": len(attackers),
                "mitigation": "BGP blackhole + ACL",
            },
            "color": "green", "ts": utc_now_iso(),
        })
        await self._set_node_state(target, NodeState.RECOVERING, 0.55)
        await self._update_threat(-20.0, "DDoS mitigation deployed")

    async def _attack_malware(self) -> None:
        patient_zero = self._pick("clients")
        self._compromised_hosts.add(patient_zero)
        await self._set_node_state(patient_zero, NodeState.COMPROMISED, 0.7)
        await self._record_event({
            "type": "attack", "name": "malware", "stage": "update",
            "details": {
                "phase": "initial_infection",
                "patient_zero": patient_zero,
                "name": self._node_meta(patient_zero)["name"],
                "message": "Malware dropper executed via phishing attachment",
                "malware_family": random.choice(["Emotet", "TrickBot", "QakBot", "Dridex"]),
            },
            "ts": utc_now_iso(),
        })
        await self._update_threat(8.0, "malware initial infection")

        all_pool = self.topology["clients"] + self.topology["servers"]
        current_wave = [patient_zero]

        for wave in range(5):
            next_wave: List[str] = []
            for src in current_wave:
                candidates = [n for n in all_pool if n not in self._compromised_hosts]
                if not candidates:
                    break
                targets = random.sample(candidates, min(random.randint(2, 4), len(candidates)))
                for victim in targets:
                    self._compromised_hosts.add(victim)
                    await self._set_node_state(victim, NodeState.COMPROMISED, 0.75)
                    vm = self._node_meta(victim)
                    sm = self._node_meta(src)
                    await self._record_event({
                        "type": "attack", "name": "malware", "stage": "update",
                        "details": {
                            "phase": "spreading",
                            "infected": victim,
                            "infected_name": vm["name"],
                            "from": src,
                            "wave": wave + 1,
                            "total_infected": len(self._compromised_hosts),
                            "vector": random.choice(["SMB-EternalBlue", "email-macro", "RDP-bruteforce", "USB"]),
                        },
                        "ts": utc_now_iso(),
                    })
                    p = self._generate_packet(normal=False, src=src, dst=victim, protocol="SMB")
                    p.update({
                        "color": "orange",
                        "src_lat": sm["lat"], "src_lng": sm["lng"],
                        "dst_lat": vm["lat"], "dst_lng": vm["lng"],
                    })
                    await self._emit_packet(p)
                    next_wave.append(victim)
                    await asyncio.sleep(0.04)

            await self._update_threat(4.0 * (wave + 1), f"malware wave {wave + 1}")
            current_wave = next_wave
            if not current_wave:
                break
            await asyncio.sleep(0.08)

        quarantine = list(self._compromised_hosts)[:min(5, len(self._compromised_hosts))]
        await self._record_event({
            "type": "defense_action", "action": "quarantine",
            "details": {
                "message": f"EDR quarantining {len(quarantine)} infected hosts",
                "hosts": quarantine,
                "tool": "CrowdStrike Falcon",
            },
            "color": "green", "ts": utc_now_iso(),
        })

    async def _attack_ransomware(self) -> None:
        # Phase 1 — lateral movement
        await self._record_event({
            "type": "attack", "name": "ransomware", "stage": "update",
            "details": {
                "phase": "lateral_movement",
                "message": "Ransomware scanning for high-value targets",
                "technique": "T1021 - Remote Services",
            },
            "ts": utc_now_iso(),
        })

        targets = random.sample(
            self.topology["servers"] + self.topology["databases"],
            min(5, len(self.topology["servers"]) + len(self.topology["databases"])),
        )

        # Phase 2 — exfiltration before encryption (double extortion)
        exfil_dst = self._pick("cloud")
        total_gb = round(random.uniform(50, 800), 1)
        await self._record_event({
            "type": "attack", "name": "ransomware", "stage": "update",
            "details": {
                "phase": "exfiltration",
                "targets": targets, "exfil_dst": exfil_dst,
                "data_size_gb": total_gb,
                "message": f"Exfiltrating {total_gb} GB before encryption — double extortion",
            },
            "ts": utc_now_iso(),
        })
        await self._update_threat(15.0, "ransomware exfiltration")
        for t in targets:
            for _ in range(3):
                p = self._generate_packet(normal=False, src=t, dst=exfil_dst, protocol="HTTPS")
                p.update({"color": "purple", "size": random.randint(50000, 65535)})
                await self._emit_packet(p)
            await asyncio.sleep(0.05)

        # Phase 3 — encrypt
        for t in targets:
            self._compromised_hosts.add(t)
            await self._set_node_state(t, NodeState.ENCRYPTED, 1.0)
            await self._record_event({
                "type": "attack", "name": "ransomware", "stage": "update",
                "details": {
                    "phase": "encrypting",
                    "locked": t,
                    "name": self._node_meta(t)["name"],
                    "state": "encrypted",
                    "extension": ".GUARDIO_LOCKED",
                    "algorithm": "AES-256-CTR + RSA-4096",
                },
                "ts": utc_now_iso(),
            })
            await self._emit_packet(self._generate_packet(normal=False, dst=t))
            await self._update_threat(8.0, f"{t} encrypted")
            await asyncio.sleep(0.07)

        # Phase 4 — ransom note
        await self._record_event({
            "type": "attack", "name": "ransomware", "stage": "update",
            "details": {
                "phase": "ransom_demand",
                "message": "YOUR FILES ARE ENCRYPTED — Pay 4.5 BTC or data is published",
                "bitcoin_address": f"bc1q{random.randint(10**15, 10**16 - 1):x}",
                "amount_btc": 4.5,
                "deadline_hours": 72,
                "encrypted_count": len(targets),
                "leak_site": "http://dark-leak[.]onion/guardio",
            },
            "ts": utc_now_iso(),
        })
        await self._update_threat(20.0, "ransom demand issued")

    async def _attack_phishing(self) -> None:
        campaign_id = f"PHISH-{random.randint(1000, 9999)}"
        lure = random.choice([
            "IT Security Update Required",
            "Your password expires in 24 hours",
            "Invoice #INV-2024-8821 attached",
            "Urgent: HR Policy Compliance",
            "DocuSign: Sign document immediately",
        ])
        await self._record_event({
            "type": "attack", "name": "phishing", "stage": "update",
            "details": {
                "phase": "campaign_start",
                "campaign_id": campaign_id,
                "lure": lure,
                "message": f"Spear-phishing campaign launched: '{lure}'",
                "targets_count": 15,
            },
            "ts": utc_now_iso(),
        })

        victims = random.sample(self.topology["clients"], min(15, len(self.topology["clients"])))
        stolen_creds: List[str] = []

        for victim in victims:
            vm = self._node_meta(victim)
            clicked = random.random() > 0.35
            if clicked:
                stolen_creds.append(victim)
                self._compromised_hosts.add(victim)
                await self._set_node_state(victim, NodeState.COMPROMISED, 0.6)
                await self._update_threat(3.0, f"credential theft: {victim}")

            await self._record_event({
                "type": "attack", "name": "phishing", "stage": "update",
                "details": {
                    "phase": "email_delivered",
                    "campaign_id": campaign_id,
                    "victim": victim,
                    "victim_lat": vm["lat"], "victim_lng": vm["lng"],
                    "clicked": clicked,
                    "credential_theft": clicked,
                    "victim_name": vm["name"],
                },
                "ts": utc_now_iso(),
            })
            p = self._generate_packet(
                normal=False, src="phisher-external", dst=victim, protocol="SMTP",
                override_src_lat=random.uniform(20, 60), override_src_lng=random.uniform(-10, 50),
            )
            p.update({"color": "orange"})
            await self._emit_packet(p)
            await asyncio.sleep(0.05)

        if stolen_creds:
            await self._record_event({
                "type": "attack", "name": "phishing", "stage": "update",
                "details": {
                    "phase": "credential_replay",
                    "accounts_compromised": len(stolen_creds),
                    "message": f"Replaying {len(stolen_creds)} stolen credentials",
                },
                "ts": utc_now_iso(),
            })
            for src in stolen_creds[:5]:
                target = self._pick("servers")
                p = self._generate_packet(normal=False, src=src, dst=target, protocol="HTTPS")
                p["color"] = "purple"
                await self._emit_packet(p)
                await asyncio.sleep(0.04)

    async def _attack_botnet(self) -> None:
        c2 = self._pick("cloud")
        bot_pool = self.topology["iot"] + self.topology["clients"]
        bots = random.sample(bot_pool, min(20, len(bot_pool)))

        await self._record_event({
            "type": "attack", "name": "botnet", "stage": "update",
            "details": {
                "phase": "recruiting",
                "c2": c2, "c2_meta": self._node_meta(c2),
                "message": "Botnet C2 beaconing — enrolling infected devices",
            },
            "ts": utc_now_iso(),
        })

        for bot in bots:
            self._compromised_hosts.add(bot)
            bm = self._node_meta(bot)
            await self._set_node_state(bot, NodeState.COMPROMISED, 0.5)
            await self._record_event({
                "type": "attack", "name": "botnet", "stage": "update",
                "details": {
                    "phase": "bot_enrolled",
                    "bot": bot,
                    "bot_lat": bm["lat"], "bot_lng": bm["lng"],
                    "controller": c2,
                    "bot_type": NODES[bot].type.value if bot in NODES else "unknown",
                },
                "ts": utc_now_iso(),
            })
            p = self._generate_packet(normal=False, src=bot, dst=c2, protocol="HTTPS")
            p["color"] = "orange"
            await self._emit_packet(p)
            await asyncio.sleep(0.025)

        await self._update_threat(15.0, f"botnet active — {len(bots)} bots")
        final_target = self._pick("servers")
        await self._record_event({
            "type": "attack", "name": "botnet", "stage": "update",
            "details": {
                "phase": "coordinated_attack",
                "target": final_target,
                "bot_count": len(bots),
                "message": f"Coordinated DDoS: {len(bots)} bots targeting {self._node_meta(final_target)['name']}",
            },
            "ts": utc_now_iso(),
        })
        for _ in range(3):
            for bot in bots:
                p = self._generate_packet(normal=False, src=bot, dst=final_target)
                p.update({"color": "red", "size": random.randint(3000, 65535)})
                await self._emit_packet(p)
            await asyncio.sleep(0.05)
        await self._set_node_state(final_target, NodeState.STRESSED, 0.92)
        await self._update_threat(10.0, "botnet DDoS")

    async def _attack_apt(self) -> None:
        await self._record_event({
            "type": "attack", "name": "apt", "stage": "update",
            "details": {
                "phase": "reconnaissance",
                "message": "APT group performing passive OSINT and network scan",
                "actor": random.choice(["APT29", "Lazarus Group", "APT41", "Sandworm"]),
                "technique": "T1595 - Active Scanning",
            },
            "ts": utc_now_iso(),
        })

        # Stealth scan — slow and low
        for _ in range(8):
            target = self._pick("servers")
            p = self._generate_packet(normal=False, dst=target, protocol="TCP",
                                      override_src_lat=random.uniform(30, 65),
                                      override_src_lng=random.uniform(10, 50))
            p.update({"src": f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}",
                      "color": "yellow", "size": random.randint(40, 120), "flags": "SYN"})
            await self._emit_packet(p)
            await asyncio.sleep(0.12)

        # Initial access via zero-day
        victim = self._pick("clients")
        cve = random.choice(["CVE-2024-38226", "CVE-2024-21413", "CVE-2024-30040"])
        self._compromised_hosts.add(victim)
        await self._set_node_state(victim, NodeState.COMPROMISED, 0.6)
        await self._record_event({
            "type": "attack", "name": "apt", "stage": "update",
            "details": {
                "phase": "initial_access",
                "technique": "T1566.001 - Spearphishing Attachment",
                "victim": victim, "cve": cve,
                "message": f"Zero-day exploit ({cve}) — foothold established",
                "privilege": "user",
            },
            "ts": utc_now_iso(),
        })
        await self._update_threat(12.0, "APT initial access")
        await asyncio.sleep(0.15)

        # Persistence + privilege escalation
        await self._record_event({
            "type": "attack", "name": "apt", "stage": "update",
            "details": {
                "phase": "persistence",
                "technique": "T1543.003 - Windows Service",
                "host": victim,
                "message": "Installing persistent implant, escalating to SYSTEM",
                "privilege": "SYSTEM",
                "implant": "custom backdoor",
            },
            "ts": utc_now_iso(),
        })
        await self._update_threat(10.0, "APT persistence + privilege escalation")
        await asyncio.sleep(0.12)

        # Lateral movement
        pivot_targets = random.sample(self.topology["servers"][:4], min(3, len(self.topology["servers"])))
        for pivot in pivot_targets:
            self._compromised_hosts.add(pivot)
            await self._set_node_state(pivot, NodeState.COMPROMISED, 0.7)
            await self._record_event({
                "type": "attack", "name": "apt", "stage": "update",
                "details": {
                    "phase": "lateral_movement",
                    "from": victim, "to": pivot,
                    "from_name": self._node_meta(victim)["name"],
                    "to_name": self._node_meta(pivot)["name"],
                    "technique": "T1021.001 - Remote Desktop Protocol",
                    "message": f"Lateral: {self._node_meta(victim)['name']} → {self._node_meta(pivot)['name']}",
                },
                "ts": utc_now_iso(),
            })
            await asyncio.sleep(0.1)

        # Data exfiltration
        exfil_size = round(random.uniform(5, 120), 1)
        await self._record_event({
            "type": "attack", "name": "apt", "stage": "update",
            "details": {
                "phase": "exfiltration",
                "technique": "T1041 - Exfiltration Over C2 Channel",
                "data_type": "PII, source_code, credentials, financial_records",
                "size_gb": exfil_size,
                "message": f"Exfiltrating {exfil_size} GB over encrypted C2 tunnel",
                "c2_protocol": "HTTPS + DNS-over-HTTPS covert channel",
            },
            "ts": utc_now_iso(),
        })
        await self._update_threat(20.0, "APT data exfiltration")
        c2 = self._pick("cloud")
        for src in list(self._compromised_hosts)[:3]:
            p = self._generate_packet(normal=False, src=src, dst=c2, protocol="HTTPS")
            p.update({"color": "purple", "size": 65535})
            await self._emit_packet(p)
            await asyncio.sleep(0.07)

    # ── snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "active_attack": self.active_attack,
            "events": len(self._events),
            "compromised_hosts": len(self._compromised_hosts),
            "threat_level": round(self._threat_level, 1),
            "threat_status": self._threat_status(),
        }


sim = Simulation()
