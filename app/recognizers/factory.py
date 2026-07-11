from app.core.config import Settings
from app.core.errors import AppError
from app.recognizers.ai import AiPlateRecognizer
from app.recognizers.base import PlateRecognizer
from app.recognizers.local import LocalPlateRecognizer
from app.recognizers.mock import MockPlateRecognizer


def create_recognizer(settings: Settings) -> PlateRecognizer:
    provider = settings.recognizer_provider
    if provider == "mock":
        return MockPlateRecognizer()
    if provider == "local":
        return LocalPlateRecognizer(settings)
    if provider == "ai":
        return AiPlateRecognizer(settings)
    raise AppError("PROVIDER_NOT_FOUND", "识别模式配置错误", f"Unsupported provider: {provider}")
