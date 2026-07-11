from pathlib import Path

from app.core.config import Settings
from app.core.errors import AppError
from app.models.recognition import RecognitionResult


class AiPlateRecognizer:
    provider_name = "ai"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def recognize(self, image_path: Path, original_filename: str) -> RecognitionResult:
        if not self._settings.ai_api_key or not self._settings.ai_endpoint:
            raise AppError("AI_PROVIDER_NOT_CONFIGURED", "AI 识别配置不完整")
        raise AppError("AI_RECOGNITION_UNAVAILABLE", "AI 识别接口暂不可用")
