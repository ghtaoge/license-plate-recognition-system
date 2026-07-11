import hashlib
import time
from pathlib import Path

from app.models.recognition import RecognitionResult


class MockPlateRecognizer:
    provider_name = "mock"

    _provinces = ["京", "沪", "粤", "浙", "苏", "鲁", "川", "渝", "湘", "鄂"]
    _letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    _digits = "0123456789"

    def recognize(self, image_path: Path, original_filename: str) -> RecognitionResult:
        started = time.perf_counter()
        digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
        plate_number = self._build_plate_number(digest)
        confidence = 0.82 + (int(digest[10:12], 16) / 255) * 0.16
        elapsed_ms = max(1, int((time.perf_counter() - started) * 1000))
        return RecognitionResult(
            plate_number=plate_number,
            confidence=round(confidence, 3),
            provider=self.provider_name,
            elapsed_ms=elapsed_ms,
            bbox=None,
            message="模拟识别完成",
        )

    def _build_plate_number(self, digest: str) -> str:
        province = self._provinces[int(digest[0:2], 16) % len(self._provinces)]
        city_letter = self._letters[int(digest[2:4], 16) % len(self._letters)]
        suffix_source = self._letters + self._digits
        suffix = "".join(
            suffix_source[int(digest[index:index + 2], 16) % len(suffix_source)]
            for index in range(4, 14, 2)
        )
        return f"{province}{city_letter}{suffix}"
