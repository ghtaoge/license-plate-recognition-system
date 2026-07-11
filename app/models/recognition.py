from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RecognitionResult:
    plate_number: str
    confidence: float
    provider: str
    elapsed_ms: int
    bbox: dict[str, int] | None
    message: str


@dataclass(frozen=True)
class RecognitionRecord:
    id: int
    plate_number: str
    confidence: float
    provider: str
    image_url: str
    elapsed_ms: int
    status: str
    error_message: str
    created_at: datetime
    message: str
