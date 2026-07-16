from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_local_provider_reports_no_plate_found(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "local")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    settings = Settings.from_env()

    with patch("app.recognizers.local.lpr3.LicensePlateCatcher") as catcher_cls:
        catcher_instance = MagicMock()
        catcher_cls.return_value = catcher_instance
        catcher_instance.return_value = []
        recognizer = LocalPlateRecognizer(settings)

        image = tmp_path / "car.png"
        image.write_bytes(b"fake-content")

        with patch("app.recognizers.local.cv2.imread", return_value=MagicMock()):
            with pytest.raises(AppError) as error:
                recognizer.recognize(image, "car.png")

            assert error.value.code == "PLATE_NOT_RECOGNIZED"
            assert error.value.message == "未识别到符合格式的车牌号"


def test_local_provider_returns_plate_from_hyperlpr(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "local")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    settings = Settings.from_env()

    with patch("app.recognizers.local.lpr3.LicensePlateCatcher") as catcher_cls:
        catcher_instance = MagicMock()
        catcher_cls.return_value = catcher_instance
        catcher_instance.return_value = [("粤B12345", 0.95, 2, [10, 20, 200, 80])]
        recognizer = LocalPlateRecognizer(settings)

        fake_image = MagicMock()
        with patch("app.recognizers.local.cv2.imread", return_value=fake_image):
            result = recognizer.recognize(tmp_path / "car.png", "car.png")

        assert result.plate_number == "粤B12345"
        assert result.confidence == 0.95
        assert result.provider == "local"
        assert result.message == "本地识别完成"
        assert result.bbox == {"x1": 10, "y1": 20, "x2": 200, "y2": 80}


def test_local_provider_filters_invalid_plate_format(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "local")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    settings = Settings.from_env()

    with patch("app.recognizers.local.lpr3.LicensePlateCatcher") as catcher_cls:
        catcher_instance = MagicMock()
        catcher_cls.return_value = catcher_instance
        catcher_instance.return_value = [("INVALID", 0.90, 2, [0, 0, 100, 50])]
        recognizer = LocalPlateRecognizer(settings)

        fake_image = MagicMock()
        with patch("app.recognizers.local.cv2.imread", return_value=fake_image):
            with pytest.raises(AppError) as error:
                recognizer.recognize(tmp_path / "car.png", "car.png")

            assert error.value.code == "PLATE_NOT_RECOGNIZED"


def test_local_provider_reports_image_read_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "local")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    settings = Settings.from_env()

    with patch("app.recognizers.local.lpr3.LicensePlateCatcher"):
        recognizer = LocalPlateRecognizer(settings)

        with patch("app.recognizers.local.cv2.imread", return_value=None):
            with pytest.raises(AppError) as error:
                recognizer.recognize(tmp_path / "missing.png", "missing.png")

            assert error.value.code == "LOCAL_RECOGNITION_FAILED"


def test_ai_provider_reports_missing_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_ENDPOINT", "")
    settings = Settings.from_env()
    recognizer = AiPlateRecognizer(settings)

    with pytest.raises(AppError) as error:
        recognizer.recognize(tmp_path / "car.jpg", "car.jpg")

    assert error.value.code == "AI_PROVIDER_NOT_CONFIGURED"
    assert error.value.message == "AI 识别配置不完整"
