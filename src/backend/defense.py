from __future__ import annotations

from typing import Any, Dict, Optional, Set
import asyncio


class DefenseManager:
    def __init__(self) -> None:
        # simple structures to control simulation behavior
        self.firewall_blocked_hosts: Set[str] = set()
        self.segments: Dict[str, Set[str]] = {}  # segment -> hosts
        self.honeypots: Set[str] = set()
        self.lock = asyncio.Lock()

    async def block_host(self, host: str) -> None:
        async with self.lock:
            self.firewall_blocked_hosts.add(host)

    async def unblock_host(self, host: str) -> None:
        async with self.lock:
            self.firewall_blocked_hosts.discard(host)

    async def is_blocked(self, host: str) -> bool:
        async with self.lock:
            return host in self.firewall_blocked_hosts

    async def add_honeypot(self, host: str) -> None:
        async with self.lock:
            self.honeypots.add(host)

    async def remove_honeypot(self, host: str) -> None:
        async with self.lock:
            self.honeypots.discard(host)

    async def create_segment(self, name: str, hosts: Set[str]) -> None:
        async with self.lock:
            self.segments[name] = set(hosts)

    async def get_snapshot(self) -> Dict[str, Any]:
        async with self.lock:
            return {
                "blocked": sorted(self.firewall_blocked_hosts),
                "honeypots": sorted(self.honeypots),
                "segments": {
                    name: sorted(hosts) for name, hosts in self.segments.items()
                },
            }

    async def segment_for(self, host: str) -> Optional[str]:
        async with self.lock:
            for name, hosts in self.segments.items():
                if host in hosts:
                    return name
        return None

    async def is_honeypot(self, host: str) -> bool:
        async with self.lock:
            return host in self.honeypots

    async def remove_segment(self, name: str) -> None:
        async with self.lock:
            self.segments.pop(name, None)

    async def reset(self) -> None:
        async with self.lock:
            self.firewall_blocked_hosts.clear()
            self.segments.clear()
            self.honeypots.clear()


defense = DefenseManager()
