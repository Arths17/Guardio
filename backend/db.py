import sqlite3
from typing import List, Dict, Any
import threading

from .utils import utc_now_iso, json_dumps

DB_PATH = "guardio.db"


class DB:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._init_lock = threading.Lock()
        self._ensure()

    def _ensure(self):
        with self._init_lock:
            conn = sqlite3.connect(self.path)
            cur = conn.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS replays (
                id TEXT PRIMARY KEY,
                ts TEXT
            )
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                replay_id TEXT,
                type TEXT,
                payload TEXT,
                ts TEXT
            )
            """)
            conn.commit()
            conn.close()

    def save_replay(self, rid: str, events: List[Dict[str, Any]]):
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO replays (id, ts) VALUES (?,?)", (rid, utc_now_iso(),))
        for ev in events:
            cur.execute("INSERT INTO events (replay_id, type, payload, ts) VALUES (?,?,?,?)", (rid, ev.get("type"), json_dumps(ev), ev.get("ts")))
        conn.commit()
        conn.close()

    def list_replays(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT r.id, r.ts, COUNT(e.id) AS event_count
            FROM replays r
            LEFT JOIN events e ON e.replay_id = r.id
            GROUP BY r.id, r.ts
            ORDER BY r.ts DESC
            """
        ).fetchall()
        conn.close()
        return [{"id": rid, "ts": ts, "event_count": count} for rid, ts, count in rows]

    def get_events(self, rid: str) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT payload FROM events WHERE replay_id = ? ORDER BY id ASC",
            (rid,),
        ).fetchall()
        conn.close()
        import json

        return [json.loads(row[0]) for row in rows]

    def purge_replay(self, rid: str):
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("DELETE FROM events WHERE replay_id = ?", (rid,))
        cur.execute("DELETE FROM replays WHERE id = ?", (rid,))
        conn.commit()
        conn.close()


db = DB()
