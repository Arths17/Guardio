from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import replay as replay_module
from .utils import json_dumps, utc_now_iso

DB_PATH = "guardio.db"
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


class DB:
    def __init__(self, path: str = DB_PATH) -> None:
        self.path: str = path
        self._init_lock: threading.Lock = threading.Lock()
        self._ensure()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _ensure(self) -> None:
        with self._init_lock:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
            conn.close()
            self._apply_migrations()

    def _apply_migrations(self) -> None:
        if not MIGRATIONS_DIR.exists():
            return

        conn = self._connect()
        cur = conn.cursor()
        applied = {
            row[0]
            for row in cur.execute(
                "SELECT name FROM schema_migrations ORDER BY applied_at ASC"
            ).fetchall()
        }

        for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if migration_path.name in applied:
                continue

            cur.executescript(migration_path.read_text(encoding="utf-8"))
            cur.execute(
                (
                    "INSERT INTO schema_migrations (name, applied_at) "
                    "VALUES (?, ?)"
                ),
                (migration_path.name, utc_now_iso()),
            )
            conn.commit()

        conn.close()

    def applied_migrations(self) -> List[str]:
        conn = self._connect()
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT name FROM schema_migrations ORDER BY applied_at ASC"
        ).fetchall()
        conn.close()
        return [row[0] for row in rows]

    def readiness_snapshot(self) -> Dict[str, Any]:
        migrations = self.applied_migrations()
        return {
            "connected": True,
            "path": self.path,
            "migrations_applied": migrations,
            "migration_count": len(migrations),
        }

    def save_replay(self, rid: str, events: List[Dict[str, Any]]) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO replays (id, ts) VALUES (?,?)",
            (
                rid,
                utc_now_iso(),
            ),
        )
        cur.execute("DELETE FROM events WHERE replay_id = ?", (rid,))
        for ev in events:
            cur.execute(
                (
                    "INSERT INTO events (replay_id, type, payload, ts) "
                    "VALUES (?,?,?,?)"
                ),
                (rid, ev.get("type"), json_dumps(ev), ev.get("ts")),
            )
        conn.commit()
        conn.close()

    def list_replays(self) -> List[Dict[str, Any]]:
        conn = self._connect()
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
        return [
            {"id": rid, "ts": ts, "event_count": count}
            for rid, ts, count in rows
        ]

    def get_events(self, rid: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT payload FROM events WHERE replay_id = ? ORDER BY id ASC",
            (rid,),
        ).fetchall()
        conn.close()
        return [json.loads(row[0]) for row in rows]

    def purge_replay(self, rid: str) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM events WHERE replay_id = ?", (rid,))
        cur.execute("DELETE FROM replays WHERE id = ?", (rid,))
        conn.commit()
        conn.close()


db: DB = DB()


def save_replay(replay_data: Dict[str, Any]) -> Dict[str, Any]:
    return replay_module.save_replay(replay_data)


def list_replays() -> List[Dict[str, Any]]:
    return replay_module.list_replays()


def get_replay(rid: str) -> Optional[Dict[str, Any]]:
    return replay_module.get_replay(rid)


def delete_replay(rid: str) -> None:
    return replay_module.delete_replay(rid)


def get_replay_summary(rid: str) -> Optional[Dict[str, Any]]:
    return replay_module.get_replay_summary(rid)
