import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    recognizer_provider: str
    ai_api_key: str
    ai_endpoint: str
    ai_model: str
    local_model_path: str
    upload_dir: Path
    database_path: Path
    upload_limit_mb: int = 8

    @property
    def available_providers(self) -> list[str]:
        return ["mock", "local", "ai"]

    @classmethod
    def from_env(cls) -> "Settings":
        upload_dir = Path(_env_value_or_default("UPLOAD_DIR", str(PROJECT_ROOT / "uploads")))
        database_url = _env_value_or_default("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'data' / 'recognitions.db'}")
        database_path = _database_url_to_path(database_url)
        return cls(
            recognizer_provider=os.getenv("RECOGNIZER_PROVIDER", "mock").strip().lower() or "mock",
            ai_api_key=os.getenv("AI_API_KEY", "").strip(),
            ai_endpoint=os.getenv("AI_ENDPOINT", "").strip(),
            ai_model=os.getenv("AI_MODEL", "").strip(),
            local_model_path=os.getenv("LOCAL_MODEL_PATH", "").strip(),
            upload_dir=upload_dir,
            database_path=database_path,
        )


def _env_value_or_default(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _database_url_to_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if database_url.startswith(prefix):
        return Path(database_url[len(prefix):])
    if "://" in database_url:
        raise ValueError("Only sqlite database URLs are supported")
    return Path(database_url)
