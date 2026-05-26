from typing import Dict, Any, Set
import asyncio


class DefenseManager:
    def __init__(self):
        # simple structures to control simulation behavior
        self.firewall_blocked_hosts: Set[str] = set()
        self.segments: Dict[str, Set[str]] = {}  # segment -> hosts
        self.honeypots: Set[str] = set()
        self.lock = asyncio.Lock()

    async def block_host(self, host: str):
        async with self.lock:
            self.firewall_blocked_hosts.add(host)

    async def unblock_host(self, host: str):
        async with self.lock:
            self.firewall_blocked_hosts.discard(host)

    async def is_blocked(self, host: str) -> bool:
        async with self.lock:
            return host in self.firewall_blocked_hosts

    async def add_honeypot(self, host: str):
        async with self.lock:
            self.honeypots.add(host)

    async def remove_honeypot(self, host: str):
        async with self.lock:
            self.honeypots.discard(host)

    async def create_segment(self, name: str, hosts: Set[str]):
        async with self.lock:
            self.segments[name] = set(hosts)

    async def remove_segment(self, name: str):
        async with self.lock:
            self.segments.pop(name, None)


defense = DefenseManager()
