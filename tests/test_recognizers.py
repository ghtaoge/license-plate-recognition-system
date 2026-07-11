from pathlib import Path

import pytest

from app.core.config import PROJECT_ROOT, Settings
from app.core.errors import AppError
from app.recognizers.ai import AiPlateRecognizer
from app.recognizers.factory import create_recognizer
from app.recognizers.local import LocalPlateRecognizer
from app.recognizers.mock import MockPlateRecognizer


def test_settings_defaults_to_mock_provider(tmp_path, monkeypatch):
    monkeypatch.delenv("RECOGNIZER_PROVIDER", raising=False)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")

    settings = Settings.from_env()

    assert settings.recognizer_provider == "mock"
    assert settings.available_providers == ["mock", "local", "ai"]
    assert settings.upload_limit_mb == 8
    assert settings.upload_dir == Path(tmp_path / "uploads")
    assert settings.database_path == Path(tmp_path / "recognitions.db")


def test_settings_treats_empty_path_env_values_as_unset(monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", "")
    monkeypatch.setenv("DATABASE_URL", "")

    settings = Settings.from_env()

    assert settings.upload_dir == PROJECT_ROOT / "uploads"
    assert settings.database_path == PROJECT_ROOT / "data" / "recognitions.db"


def test_settings_rejects_unsupported_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/recognitions")

    with pytest.raises(ValueError, match="Only sqlite database URLs are supported"):
        Settings.from_env()


def test_mock_recognizer_returns_stable_plate_number(tmp_path):
    image = tmp_path / "car.jpg"
    image.write_bytes(b"same-image-content")
    recognizer = MockPlateRecognizer()

    first = recognizer.recognize(image, "car.jpg")
    second = recognizer.recognize(image, "car.jpg")

    assert first.plate_number == second.plate_number
    assert first.provider == "mock"
    assert 0.82 <= first.confidence <= 0.98
    assert first.message == "模拟识别完成"


def test_factory_selects_mock_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    settings = Settings.from_env()

    recognizer = create_recognizer(settings)

    assert isinstance(recognizer, MockPlateRecognizer)


def test_local_provider_reports_missing_model_path(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL_PATH", "")
    settings = Settings.from_env()
    recognizer = LocalPlateRecognizer(settings)

    with pytest.raises(AppError) as error:
        recognizer.recognize(tmp_path / "car.jpg", "car.jpg")

    assert error.value.code == "LOCAL_MODEL_NOT_CONFIGURED"
    assert error.value.message == "本地识别未配置模型路径"


def test_ai_provider_reports_missing_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_ENDPOINT", "")
    settings = Settings.from_env()
    recognizer = AiPlateRecognizer(settings)

    with pytest.raises(AppError) as error:
        recognizer.recognize(tmp_path / "car.jpg", "car.jpg")

    assert error.value.code == "AI_PROVIDER_NOT_CONFIGURED"
    assert error.value.message == "AI 识别配置不完整"
