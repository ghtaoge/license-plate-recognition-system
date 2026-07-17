from datetime import datetime, timezone
from pathlib import Path

from app.core.errors import AppError
from app.models.recognition import RecognitionRecord
from app.recognizers.base import PlateRecognizer
from app.services.history_repository import HistoryRepository
from app.services.storage_service import StorageService


class RecognitionService:
    _allowed_content_types = {"image/jpeg", "image/png", "image/webp"}

    def __init__(
        self,
        storage_service: StorageService,
        history_repository: HistoryRepository,
        recognizer: PlateRecognizer,
        upload_root: Path,
    ) -> None:
        self._storage_service = storage_service
        self._history_repository = history_repository
        self._recognizer = recognizer
        self._upload_root = upload_root

    def recognize_upload(self, content: bytes, filename: str, content_type: str) -> RecognitionRecord:
        if content_type not in self._allowed_content_types:
            raise AppError("UNSUPPORTED_FILE_TYPE", "仅支持 JPG、PNG、WEBP 图片")
        if not content:
            raise AppError("EMPTY_FILE", "请先选择图片")

        image_path = self._storage_service.save_upload(content, filename)
        image_url = f"/uploads/{image_path.name}"
        try:
            result = self._recognizer.recognize(image_path, filename)
            record = RecognitionRecord(
                id=0,
                plate_number=result.plate_number,
                confidence=result.confidence,
                provider=result.provider,
                image_url=image_url,
                elapsed_ms=result.elapsed_ms,
                status="success",
                error_message="",
                created_at=datetime.now(timezone.utc),
                message=result.message,
                bbox=result.bbox,
            )
            return self._history_repository.create(record)
        except AppError as error:
            failure = RecognitionRecord(
                id=0,
                plate_number="",
                confidence=0,
                provider=getattr(self._recognizer, "provider_name", "unknown"),
                image_url=image_url,
                elapsed_ms=0,
                status="failed",
                error_message=error.message,
                created_at=datetime.now(timezone.utc),
                message=error.message,
            )
            self._history_repository.create(failure)
            raise
