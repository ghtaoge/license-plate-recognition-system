import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from app.models.recognition import RecognitionRecord


class HistoryRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS recognitions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plate_number TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        provider TEXT NOT NULL,
                        image_url TEXT NOT NULL,
                        elapsed_ms INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        error_message TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        message TEXT NOT NULL
                    )
                    """
                )

    def create(self, record: RecognitionRecord) -> RecognitionRecord:
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO recognitions (
                        plate_number, confidence, provider, image_url, elapsed_ms,
                        status, error_message, created_at, message
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.plate_number,
                        record.confidence,
                        record.provider,
                        record.image_url,
                        record.elapsed_ms,
                        record.status,
                        record.error_message,
                        record.created_at.isoformat(),
                        record.message,
                    ),
                )
                record_id = int(cursor.lastrowid)
            return RecognitionRecord(
                id=record_id,
                plate_number=record.plate_number,
                confidence=record.confidence,
                provider=record.provider,
                image_url=record.image_url,
                elapsed_ms=record.elapsed_ms,
                status=record.status,
                error_message=record.error_message,
                created_at=record.created_at,
                message=record.message,
            )

    def list_recent(self, limit: int = 20) -> list[RecognitionRecord]:
        bounded_limit = min(max(limit, 1), 100)
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, plate_number, confidence, provider, image_url, elapsed_ms,
                       status, error_message, created_at, message
                FROM recognitions
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT ?
                """,
                (bounded_limit,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _row_to_record(self, row: sqlite3.Row) -> RecognitionRecord:
        return RecognitionRecord(
            id=int(row["id"]),
            plate_number=str(row["plate_number"]),
            confidence=float(row["confidence"]),
            provider=str(row["provider"]),
            image_url=str(row["image_url"]),
            elapsed_ms=int(row["elapsed_ms"]),
            status=str(row["status"]),
            error_message=str(row["error_message"]),
            created_at=datetime.fromisoformat(str(row["created_at"])).astimezone(timezone.utc),
            message=str(row["message"]),
        )
