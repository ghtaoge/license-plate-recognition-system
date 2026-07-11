from pathlib import Path

from app.core.config import Settings
from app.core.errors import AppError
from app.models.recognition import RecognitionResult


class LocalPlateRecognizer:
    provider_name = "local"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def recognize(self, image_path: Path, original_filename: str) -> RecognitionResult:
        if not self._settings.local_model_path:
            raise AppError("LOCAL_MODEL_NOT_CONFIGURED", "本地识别未配置模型路径")
        raise AppError("LOCAL_RECOGNITION_UNAVAILABLE", "本地识别引擎暂不可用")
