import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.config import Settings
from app.core.errors import AppError
from app.models.recognition import RecognitionRecord
from app.recognizers.factory import create_recognizer
from app.services.history_repository import HistoryRepository
from app.services.recognition_service import RecognitionService
from app.services.storage_service import StorageService


router = APIRouter()


def get_settings() -> Settings:
    return Settings.from_env()


def get_repository(settings: Settings = Depends(get_settings)) -> HistoryRepository:
    repository = HistoryRepository(settings.database_path)
    repository.initialize()
    return repository


def get_recognition_service(
    settings: Settings = Depends(get_settings),
    repository: HistoryRepository = Depends(get_repository),
) -> RecognitionService:
    recognizer = create_recognizer(settings)
    storage = StorageService(settings.upload_dir)
    return RecognitionService(storage, repository, recognizer, settings.upload_dir)


@router.get("/config")
def get_config(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "provider": settings.recognizer_provider,
        "available_providers": settings.available_providers,
        "upload_limit_mb": settings.upload_limit_mb,
    }


@router.post("/recognitions")
async def create_recognition(
    file: UploadFile = File(...),
    service: RecognitionService = Depends(get_recognition_service),
) -> dict[str, object]:
    content = await file.read()
    try:
        record = await asyncio.to_thread(
            service.recognize_upload, content, file.filename or "upload.jpg", file.content_type or ""
        )
        return _record_to_dict(record)
    except AppError as error:
        raise HTTPException(
            status_code=400,
            detail={"code": error.code, "message": error.message, "detail": error.detail},
        ) from error


@router.get("/recognitions")
def list_recognitions(
    limit: int = 20,
    repository: HistoryRepository = Depends(get_repository),
) -> list[dict[str, object]]:
    return [_record_to_dict(record) for record in repository.list_recent(limit)]


def _record_to_dict(record: RecognitionRecord) -> dict[str, object]:
    return {
        "id": record.id,
        "plate_number": record.plate_number,
        "confidence": record.confidence,
        "provider": record.provider,
        "image_url": record.image_url,
        "elapsed_ms": record.elapsed_ms,
        "status": record.status,
        "error_message": record.error_message,
        "created_at": record.created_at.isoformat(),
        "message": record.message,
    }
