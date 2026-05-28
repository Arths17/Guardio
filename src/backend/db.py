from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

from . import replay as replay_module
from .utils import json_dumps, utc_now_iso

logger = logging.getLogger("guardio.db")

DB_PATH = "guardio.db"
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


class DB:
    def __init__(self, path: str = DB_PATH, max_workers: int = 10) -> None:
        self.path = path
        self._init_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._ensure()

    def _get_raw_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
            timeout=30.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        return conn

    def _ensure(self) -> None:
        with self._init_lock:
            with self._get_raw_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        name TEXT PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    )
                    """)
            self._apply_migrations()

    def _apply_migrations(self) -> None:
        if not MIGRATIONS_DIR.exists():
            return

        with self._get_raw_connection() as conn:
            cur = conn.cursor()
            applied = {
                row[0]
                for row in cur.execute(
                    "SELECT name FROM schema_migrations " "ORDER BY applied_at ASC"
                ).fetchall()
            }

            for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if migration_path.name in applied:
                    continue

                cur.executescript(migration_path.read_text(encoding="utf-8"))
                cur.execute(
                    (
                        "INSERT INTO schema_migrations "
                        "(name, applied_at) VALUES (?, ?)"
                    ),
                    (migration_path.name, utc_now_iso()),
                )
                conn.commit()

    def applied_migrations(self) -> List[str]:
        with self._get_raw_connection() as conn:
            cur = conn.cursor()
            rows = cur.execute(
                "SELECT name FROM schema_migrations ORDER BY applied_at ASC"
            ).fetchall()
            return [row[0] for row in rows]

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
            self._executor,
            self.readiness_snapshot,
        )

    def save_replay(self, rid: str, events: List[Dict[str, Any]]) -> None:
        with self._get_raw_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO replays (id, ts) VALUES (?, ?)",
                (rid, utc_now_iso()),
            )
            cur.execute("DELETE FROM events WHERE replay_id = ?", (rid,))
            for ev in events:
                cur.execute(
                    (
                        "INSERT INTO events "
                        "(replay_id, type, payload, ts) VALUES (?, ?, ?, ?)"
                    ),
                    (rid, ev.get("type"), json_dumps(ev), ev.get("ts")),
                )
            conn.commit()

    async def save_replay_async(
        self,
        rid: str,
        events: List[Dict[str, Any]],
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self._executor,
            self.save_replay,
            rid,
            events,
        )

    def list_replays(self) -> List[Dict[str, Any]]:
        with self._get_raw_connection() as conn:
            rows = conn.execute("""
                SELECT r.id, r.ts, COUNT(e.id) AS event_count
                FROM replays r
                LEFT JOIN events e ON e.replay_id = r.id
                GROUP BY r.id, r.ts
                ORDER BY r.ts DESC
                """).fetchall()
        return [{"id": rid, "ts": ts, "event_count": count} for rid, ts, count in rows]

    async def list_replays_async(self) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self.list_replays)

    def get_events(self, rid: str) -> List[Dict[str, Any]]:
        with self._get_raw_connection() as conn:
            rows = conn.execute(
                "SELECT payload FROM events " "WHERE replay_id = ? ORDER BY id ASC",
                (rid,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    async def get_events_async(self, rid: str) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self.get_events, rid)

    def purge_replay(self, rid: str) -> None:
        with self._get_raw_connection() as conn:
            conn.execute("DELETE FROM events WHERE replay_id = ?", (rid,))
            conn.execute("DELETE FROM replays WHERE id = ?", (rid,))
            conn.commit()

    async def purge_replay_async(self, rid: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self.purge_replay, rid)

    async def initialize_async(self) -> None:
        logger.info("Hardening database engine states, setting up WAL mode parameters.")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._ensure)

    async def close_async(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._executor.shutdown)


_db = DB()


class _DBProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(_db, name)


db = _DBProxy()


def save_replay(replay_data: Dict[str, Any]):
    return replay_module.save_replay(replay_data)


def list_replays():
    return replay_module.list_replays()


def get_replay(rid: str):
    return replay_module.get_replay(rid)


def delete_replay(rid: str):
    return replay_module.delete_replay(rid)


def get_replay_summary(rid: str):
    return replay_module.get_replay_summary(rid)
