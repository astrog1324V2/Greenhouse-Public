from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .sensors import SensorReading


SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    temperature_c REAL,
    humidity_pct REAL,
    light_lux REAL,
    measured_at_utc TEXT NOT NULL,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_readings_measured_at
    ON readings (measured_at_utc DESC);
"""


@dataclass(frozen=True)
class StoredReading:
    id: int
    device_id: str
    temperature_c: float | None
    humidity_pct: float | None
    light_lux: float | None
    measured_at_utc: str
    error: str | None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_connection(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(get_connection(db_path)) as connection:
        connection.executescript(SCHEMA)
        connection.commit()


def insert_reading(db_path: Path, device_id: str, reading: SensorReading) -> StoredReading:
    measured_at_utc = utc_now_iso()
    with closing(get_connection(db_path)) as connection:
        cursor = connection.execute(
            """
            INSERT INTO readings (
                device_id, temperature_c, humidity_pct, light_lux, measured_at_utc, error
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                reading.temperature_c,
                reading.humidity_pct,
                reading.light_lux,
                measured_at_utc,
                reading.error,
            ),
        )
        connection.commit()
        row_id = int(cursor.lastrowid)

    return StoredReading(
        id=row_id,
        device_id=device_id,
        temperature_c=reading.temperature_c,
        humidity_pct=reading.humidity_pct,
        light_lux=reading.light_lux,
        measured_at_utc=measured_at_utc,
        error=reading.error,
    )


def fetch_latest_reading(db_path: Path) -> StoredReading | None:
    with closing(get_connection(db_path)) as connection:
        row = connection.execute(
            """
            SELECT id, device_id, temperature_c, humidity_pct, light_lux, measured_at_utc, error
            FROM readings
            ORDER BY measured_at_utc DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
    return _row_to_reading(row) if row else None


def fetch_history(db_path: Path, *, hours: int = 24, limit: int = 500) -> list[StoredReading]:
    since = datetime.now(timezone.utc) - timedelta(hours=max(1, hours))
    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT id, device_id, temperature_c, humidity_pct, light_lux, measured_at_utc, error
            FROM readings
            WHERE measured_at_utc >= ?
            ORDER BY measured_at_utc DESC, id DESC
            LIMIT ?
            """,
            (since.replace(microsecond=0).isoformat(), limit),
        ).fetchall()
    return [_row_to_reading(row) for row in rows]


def count_readings(db_path: Path) -> int:
    with closing(get_connection(db_path)) as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM readings").fetchone()
    return int(row["count"])


def _row_to_reading(row: sqlite3.Row) -> StoredReading:
    return StoredReading(
        id=int(row["id"]),
        device_id=str(row["device_id"]),
        temperature_c=row["temperature_c"],
        humidity_pct=row["humidity_pct"],
        light_lux=row["light_lux"],
        measured_at_utc=str(row["measured_at_utc"]),
        error=row["error"],
    )

