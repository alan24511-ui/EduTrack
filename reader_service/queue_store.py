"""Cola SQLite durable para lecturas RFID aún no confirmadas por la API."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class ReadingQueue:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS pending_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT NOT NULL,
                    device_code TEXT NOT NULL,
                    captured_at TEXT NOT NULL
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def enqueue(self, uid: str, device_code: str, captured_at: str) -> int:
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO pending_readings (uid, device_code, captured_at) VALUES (?, ?, ?)",
                (uid, device_code, captured_at),
            )
            return int(cursor.lastrowid)

    def pending(self, limit: int = 100) -> list[tuple[int, str, str, str]]:
        with self._connect() as db:
            return list(db.execute(
                "SELECT id, uid, device_code, captured_at FROM pending_readings ORDER BY id LIMIT ?",
                (limit,),
            ))

    def acknowledge(self, reading_id: int) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM pending_readings WHERE id = ?", (reading_id,))

    def count(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT count(*) FROM pending_readings").fetchone()[0])
