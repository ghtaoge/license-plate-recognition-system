import re
import time
from pathlib import Path

import cv2
import hyperlpr3 as lpr3

from app.core.config import Settings
from app.core.errors import AppError
from app.models.recognition import RecognitionResult


_PROVINCES = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"
_LETTER = "A-HJ-NP-Z"
_ALPHANUMERIC = "A-HJ-NP-Z0-9"
_NEW_ENERGY_PLATE = re.compile(
    rf"[{_PROVINCES}][{_LETTER}](?:[DF][{_ALPHANUMERIC}][0-9]{{4}}|[0-9]{{5}}[DF])(?![A-Z0-9])"
)
_CONVENTIONAL_PLATE = re.compile(
    rf"[{_PROVINCES}][{_LETTER}][{_ALPHANUMERIC}]{{5}}(?![A-Z0-9])"
)


class LocalPlateRecognizer:
    provider_name = "local"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._catcher = lpr3.LicensePlateCatcher()

    def recognize(self, image_path: Path, original_filename: str) -> RecognitionResult:
        started = time.perf_counter()
        image = self._load_image(image_path)
        results = self._catcher(image)

        if not results:
            raise AppError("PLATE_NOT_RECOGNIZED", "未识别到符合格式的车牌号")

        plate_number, confidence, plate_type, box = self._pick_best(results)
        elapsed_ms = max(1, int((time.perf_counter() - started) * 1000))

        return RecognitionResult(
            plate_number=plate_number,
            confidence=confidence,
            provider=self.provider_name,
            elapsed_ms=elapsed_ms,
            bbox=self._box_to_dict(box),
            message="本地识别完成",
        )

    def _load_image(self, image_path: Path) -> "cv2.MatTyping.MatLike":
        image = cv2.imread(str(image_path))
        if image is None:
            raise AppError(
                "LOCAL_RECOGNITION_FAILED",
                "本地识别引擎执行失败",
                f"Cannot read image: {image_path}",
            )
        return image

    def _pick_best(self, results: list) -> tuple[str, float, int, list[int]]:
        best_plate = ""
        best_confidence = 0.0
        best_type = 0
        best_box: list[int] = []

        for plate_number, confidence, plate_type, box in results:
            normalized = plate_number.upper()
            native_confidence = float(confidence)
            if _NEW_ENERGY_PLATE.fullmatch(normalized) or _CONVENTIONAL_PLATE.fullmatch(normalized):
                if native_confidence > best_confidence:
                    best_plate = normalized
                    best_confidence = native_confidence
                    best_type = int(plate_type)
                    best_box = [int(v) for v in box]

        if not best_plate:
            raise AppError("PLATE_NOT_RECOGNIZED", "未识别到符合格式的车牌号")

        confidence = round(min(1.0, max(0.0, best_confidence)), 3)
        return best_plate, confidence, best_type, best_box

    def _box_to_dict(self, box: list[int]) -> dict[str, int] | None:
        if not box or len(box) < 4:
            return None
        x1, y1, x2, y2 = box[:4]
        return {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)}
