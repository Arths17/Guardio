from datetime import datetime

from .utils import utc_now_iso


class IDS:
    def __init__(self):
        # simple thresholds
        self.suspicion_threshold = 0.7

    def score_packet(self, pkt: dict) -> float:
        # heuristic scoring based on color and size
        score = 0.0
        color = pkt.get("color")
        size = pkt.get("size", 0)
        if color == "red":
            score += 0.7
        elif color == "yellow":
            score += 0.4
        if size > 5000:
            score += 0.2
        # minor randomness via dst hash
        score += (hash(pkt.get("dst", "")) % 10) / 100.0
        return min(1.0, score)

    def alert_for(self, pkt: dict) -> dict | None:
        score = self.score_packet(pkt)
        if score >= self.suspicion_threshold:
            return {"type": "alert", "level": "high" if score > 0.85 else "medium", "score": score, "packet": pkt, "ts": utc_now_iso()}
        return None


ids = IDS()
