from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import DefaultDict, Deque, Optional, Tuple
from uuid import uuid4

from backend.utils import utc_now_iso

_ATTACK_PROTOCOLS = frozenset({
    "TCP-SYN", "UDP-FLOOD", "ICMP-FLOOD",
    "NTP-AMP", "HTTP-POST", "SMB", "RDP",
})


class _RateWindow:
    """Sliding-window packet counter per key."""

    def __init__(self, window: float = 5.0, threshold: int = 30) -> None:
        self.window = window
        self.threshold = threshold
        self._buckets: DefaultDict[str, Deque[float]] = defaultdict(deque)

    def record(self, key: str) -> int:
        now = time.monotonic()
        dq = self._buckets[key]
        cutoff = now - self.window
        while dq and dq[0] < cutoff:
            dq.popleft()
        dq.append(now)
        return len(dq)

    def is_excessive(self, key: str) -> bool:
        return self.record(key) > self.threshold

    def clear(self) -> None:
        self._buckets.clear()


class IDS:
    def __init__(self) -> None:
        self.suspicion_threshold = 0.65
        self._src_rate = _RateWindow(window=5.0, threshold=25)
        self._dst_rate = _RateWindow(window=5.0, threshold=50)
        self._pair_hits: DefaultDict[Tuple[str, str], int] = defaultdict(int)

    def score_packet(self, pkt: dict) -> Tuple[float, str]:
        score = 0.0
        reason = ""

        color = pkt.get("color", "blue")
        protocol = pkt.get("protocol", "")
        size = pkt.get("size", 0)
        flags = pkt.get("flags", "")
        src = str(pkt.get("src", ""))
        dst = str(pkt.get("dst", ""))

        # Simulation color signals
        if color == "red":
            score += 0.50
            reason = "malicious traffic"
        elif color in ("orange", "yellow"):
            score += 0.30
            reason = "suspicious traffic"

        # Protocol anomalies
        if protocol in _ATTACK_PROTOCOLS:
            score += 0.40
            reason = f"attack protocol: {protocol}"

        # Suspicious TCP flags
        if flags in ("SYN", "RST", "FIN"):
            score += 0.10

        # Oversized packets
        if size > 10_000:
            score += 0.20
            reason = reason or "oversized packet"

        # Rate-based detection
        src_rate = self._src_rate.record(src)
        dst_rate = self._dst_rate.record(dst)

        if src_rate > 25:
            score += min(0.40, (src_rate - 25) / 50.0)
            reason = f"high rate from {src}: {src_rate}/5s"

        if dst_rate > 50:
            score += min(0.30, (dst_rate - 50) / 100.0)
            reason = reason or f"flood to {dst}: {dst_rate}/5s"

        # Repeated src-dst pair
        pair = (src, dst)
        self._pair_hits[pair] += 1
        if self._pair_hits[pair] > 20:
            score += 0.20
            reason = reason or "repeated src→dst pair"

        return min(1.0, score), reason

    def alert_for(self, pkt: dict) -> Optional[dict]:
        score, reason = self.score_packet(pkt)
        if score < self.suspicion_threshold:
            return None
        if score > 0.90:
            level = "critical"
        elif score > 0.75:
            level = "high"
        else:
            level = "medium"
        return {
            "type": "alert",
            "alert_id": uuid4().hex[:8],
            "level": level,
            "score": round(score, 3),
            "reason": reason,
            "src": pkt.get("src"),
            "dst": pkt.get("dst"),
            "protocol": pkt.get("protocol"),
            "src_lat": pkt.get("src_lat", 0.0),
            "src_lng": pkt.get("src_lng", 0.0),
            "dst_lat": pkt.get("dst_lat", 0.0),
            "dst_lng": pkt.get("dst_lng", 0.0),
            "ts": utc_now_iso(),
        }

    def reset_rates(self) -> None:
        self._src_rate.clear()
        self._dst_rate.clear()
        self._pair_hits.clear()


ids = IDS()


# Legacy module-level helpers kept for backwards compatibility
def score_packet(pkt: dict) -> float:
    payload = str(pkt.get("payload", "")).lower()
    if payload:
        s = 0.0
        if "admin" in payload:
            s += 0.4
        if "passwd" in payload or "shadow" in payload:
            s += 0.8
        if "/etc/passwd" in payload:
            s += 0.2
        return min(1.0, s)
    return ids.score_packet(pkt)[0]


def generate_alert(pkt: dict, score: float) -> dict:
    return {
        "alert_id": uuid4().hex,
        "source_ip": pkt.get("source_ip"),
        "destination_ip": pkt.get("destination_ip"),
        "protocol": pkt.get("protocol"),
        "payload": pkt.get("payload"),
        "score": score,
        "timestamp": utc_now_iso(),
    }
