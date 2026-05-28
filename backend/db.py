from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

from backend.utils import json_dumps, utc_now_iso

logger = logging.getLogger("guardio.db")

DB_PATH = "guardio.db"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

_tls = threading.local()  # thread-local connection cache


class DB:
    def __init__(
        self, path: str = DB_PATH, max_workers: int = 10
    ) -> None:
        self.path = path
        self._init_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="db"
        )
        self._ensure()

    # ── connection management ──────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        """Return a per-thread cached connection, creating it on first use."""
        conn: sqlite3.Connection | None = getattr(_tls, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                self.path,
                check_same_thread=False,
                timeout=30.0,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=30000;")
            conn.execute("PRAGMA foreign_keys=ON;")
            _tls.conn = conn
        return conn

    # ── schema ─────────────────────────────────────────────────────────────

    def _ensure(self) -> None:
        with self._init_lock:
            conn = self._conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
            conn.commit()
            self._apply_migrations()

    def _apply_migrations(self) -> None:
        if not MIGRATIONS_DIR.exists():
            return
        conn = self._conn()
        applied = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM schema_migrations ORDER BY applied_at"
            ).fetchall()
        }
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                continue
            conn.executescript(path.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_migrations"
                " (name, applied_at) VALUES (?, ?)",
                (path.name, utc_now_iso()),
            )
            conn.commit()

    def applied_migrations(self) -> List[str]:
        rows = self._conn().execute(
            "SELECT name FROM schema_migrations ORDER BY applied_at"
        ).fetchall()
        return [r[0] for r in rows]

    def readiness_snapshot(self) -> Dict[str, Any]:
        migrations = self.applied_migrations()
        return {
            "connected": True,
            "path": self.path,
            "migrations_applied": migrations,
            "migration_count": len(migrations),
        }

    async def readiness_snapshot_async(self) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self.readiness_snapshot
        )

    # ── replays ────────────────────────────────────────────────────────────

    def save_replay(self, rid: str, events: List[Dict[str, Any]]) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO replays (id, ts) VALUES (?, ?)",
            (rid, utc_now_iso()),
        )
        conn.execute("DELETE FROM events WHERE replay_id = ?", (rid,))
        conn.executemany(
            "INSERT INTO events (replay_id, type, payload, ts)"
            " VALUES (?, ?, ?, ?)",
            [
                (rid, ev.get("type"), json_dumps(ev), ev.get("ts"))
                for ev in events
            ],
        )
        conn.commit()

    async def save_replay_async(
        self, rid: str, events: List[Dict[str, Any]]
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self._executor, self.save_replay, rid, events
        )

    def list_replays(self) -> List[Dict[str, Any]]:
        rows = self._conn().execute("""
            SELECT r.id, r.ts, COUNT(e.id) AS event_count
            FROM replays r
            LEFT JOIN events e ON e.replay_id = r.id
            GROUP BY r.id, r.ts
            ORDER BY r.ts DESC
        """).fetchall()
        return [
            {"id": r[0], "ts": r[1], "event_count": r[2]} for r in rows
        ]

    async def list_replays_async(self) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self.list_replays)

    def get_events(self, rid: str) -> List[Dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT payload FROM events WHERE replay_id = ? ORDER BY id",
            (rid,),
        ).fetchall()
        return [json.loads(r[0]) for r in rows]

    async def get_events_async(self, rid: str) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self.get_events, rid
        )

    def purge_replay(self, rid: str) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM events WHERE replay_id = ?", (rid,))
        conn.execute("DELETE FROM replays WHERE id = ?", (rid,))
        conn.commit()

    async def purge_replay_async(self, rid: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self.purge_replay, rid)

    # ── lifecycle ──────────────────────────────────────────────────────────

    async def initialize_async(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._ensure)

    async def close_async(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._executor.shutdown)


db = DB()


# Lazy re-exports — avoids circular import with backend.replay
def save_replay(replay_data: Dict[str, Any]) -> Dict[str, Any]:
    from backend import replay as _r
    return _r.save_replay(replay_data)


def list_replays() -> List[Dict[str, Any]]:
    from backend import replay as _r
    return _r.list_replays()


def get_replay(rid: str):
    from backend import replay as _r
    return _r.get_replay(rid)


def delete_replay(rid: str) -> None:
    from backend import replay as _r
    return _r.delete_replay(rid)


def get_replay_summary(rid: str):
    from backend import replay as _r
    return _r.get_replay_summary(rid)
