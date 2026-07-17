import asyncio
import math

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.core.config import Settings
from app.core.errors import AppError
from app.models.recognition import RecognitionRecord
from app.recognizers.factory import create_recognizer
from app.services.history_repository import HistoryRepository
from app.services.recognition_service import RecognitionService
from app.services.storage_service import StorageService


router = APIRouter()


def _get_settings(request: Request) -> Settings:
    return request.app.state.settings


def _get_repository(request: Request) -> HistoryRepository:
    return request.app.state.repository


def get_recognition_service(
    request: Request,
    settings: Settings = Depends(_get_settings),
    repository: HistoryRepository = Depends(_get_repository),
) -> RecognitionService:
    recognizer = create_recognizer(settings)
    storage = StorageService(settings.upload_dir)
    return RecognitionService(storage, repository, recognizer, settings.upload_dir)


@router.get("/config")
def get_config(settings: Settings = Depends(_get_settings)) -> dict[str, object]:
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
    page: int = 1,
    repository: HistoryRepository = Depends(_get_repository),
) -> dict[str, object]:
    bounded_limit = min(max(limit, 1), 100)
    total = repository.count()
    max_page = max(1, math.ceil(total / bounded_limit))
    bounded_page = min(max(page, 1), max_page)
    records = repository.list_recent(bounded_limit, bounded_page)
    return {
        "records": [_record_to_dict(record) for record in records],
        "total": total,
        "page": bounded_page,
        "limit": bounded_limit,
    }


@router.delete("/recognitions/{record_id}")
def delete_recognition(
    record_id: int,
    repository: HistoryRepository = Depends(_get_repository),
) -> dict[str, object]:
    deleted = repository.delete(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "记录不存在"})
    return {"id": record_id, "deleted": True}


@router.delete("/recognitions")
def delete_all_recognitions(
    repository: HistoryRepository = Depends(_get_repository),
) -> dict[str, object]:
    count = repository.delete_all()
    return {"deleted_count": count}


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
        "bbox": record.bbox,
    }
