import sqlite3
from typing import List, Dict, Any
from datetime import datetime
import threading

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
        cur.execute("INSERT OR REPLACE INTO replays (id, ts) VALUES (?,?)", (rid, datetime.utcnow().isoformat() + "Z"))
        for ev in events:
            cur.execute("INSERT INTO events (replay_id, type, payload, ts) VALUES (?,?,?,?)", (rid, ev.get("type"), str(ev), ev.get("ts")))
        conn.commit()
        conn.close()


db = DB()
