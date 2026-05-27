from uuid import uuid4

from backend.utils import utc_now_iso


class IDS:
    def __init__(self):
        self.suspicion_threshold = 0.7

    def score_packet(self, pkt: dict) -> float:
        score = 0.0
        color = pkt.get("color")
        size = pkt.get("size", 0)
        if color == "red":
            score += 0.7
        elif color == "yellow":
            score += 0.4
        if size > 5000:
            score += 0.2
        score += (hash(pkt.get("dst", "")) % 10) / 100.0
        return min(1.0, score)

    def alert_for(self, pkt: dict) -> dict | None:
        score = self.score_packet(pkt)
        if score >= self.suspicion_threshold:
            return {
                "type": "alert",
                "level": "high" if score > 0.85 else "medium",
                "score": score,
                "packet": pkt,
                "ts": utc_now_iso(),
            }
        return None


ids = IDS()


def score_packet(pkt: dict) -> float:
    payload = str(pkt.get("payload", "")).lower()
    if payload:
        score = 0.0
        if "admin" in payload:
            score += 0.4
        if "passwd" in payload or "shadow" in payload:
            score += 0.8
        if "/etc/passwd" in payload:
            score += 0.2
        return min(1.0, score)

    return ids.score_packet(pkt)


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
