import re
from pathlib import Path
from uuid import uuid4


class StorageService:
    _allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp"}
    _max_stem_length = 48

    def __init__(self, upload_dir: Path) -> None:
        self._upload_dir = upload_dir
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, content: bytes, original_filename: str) -> Path:
        suffix = Path(original_filename).suffix.lower()
        if suffix not in self._allowed_suffixes:
            suffix = ".jpg"
        safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(original_filename).stem).strip("-")
        safe_stem = safe_stem[: self._max_stem_length]
        filename = f"{uuid4().hex}-{safe_stem or 'upload'}{suffix}"
        target = self._upload_dir / filename
        target.write_bytes(content)
        return target
