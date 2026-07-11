from pathlib import Path
from typing import Protocol

from app.models.recognition import RecognitionResult


class PlateRecognizer(Protocol):
    provider_name: str

    def recognize(self, image_path: Path, original_filename: str) -> RecognitionResult:
        ...
