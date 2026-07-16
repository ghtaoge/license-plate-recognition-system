from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.models.recognition import RecognitionRecord
from app.services.history_repository import HistoryRepository
from app.services.storage_service import StorageService


def test_storage_service_saves_file_with_safe_generated_name(tmp_path):
    storage = StorageService(tmp_path)

    saved = storage.save_upload(b"image-content", "粤B 12345.jpg")

    assert saved.exists()
    assert saved.read_bytes() == b"image-content"
    assert saved.suffix == ".jpg"
    assert " " not in saved.name


def test_storage_service_caps_long_generated_filename(tmp_path):
    storage = StorageService(tmp_path)
    long_stem = "a" * 300

    saved = storage.save_upload(b"image-content", f"{long_stem}.png")

    assert saved.exists()
    assert len(saved.name) <= 90
    assert saved.suffix == ".png"


def test_history_repository_returns_newest_records_first(tmp_path):
    repository = HistoryRepository(tmp_path / "recognitions.db")
    repository.initialize()
    older = RecognitionRecord(
        id=0,
        plate_number="粤B12345",
        confidence=0.91,
        provider="mock",
        image_url="/uploads/older.jpg",
        elapsed_ms=12,
        status="success",
        error_message="",
        created_at=datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc),
        message="模拟识别完成",
    )
    newer = RecognitionRecord(
        id=0,
        plate_number="京A88888",
        confidence=0.95,
        provider="mock",
        image_url="/uploads/newer.jpg",
        elapsed_ms=8,
        status="success",
        error_message="",
        created_at=datetime(2026, 7, 11, 10, 0, tzinfo=timezone.utc),
        message="模拟识别完成",
    )

    repository.create(older)
    repository.create(newer)

    records = repository.list_recent(limit=10)
    assert [record.plate_number for record in records] == ["京A88888", "粤B12345"]


def test_history_repository_closes_database_connections_after_operations(tmp_path):
    database_path = tmp_path / "recognitions.db"
    repository = HistoryRepository(database_path)
    repository.initialize()
    record = RecognitionRecord(
        id=0,
        plate_number="沪C12345",
        confidence=0.89,
        provider="mock",
        image_url="/uploads/record.jpg",
        elapsed_ms=15,
        status="success",
        error_message="",
        created_at=datetime(2026, 7, 11, 11, 0, tzinfo=timezone.utc),
        message="模拟识别完成",
    )

    repository.create(record)
    records = repository.list_recent(limit=10)

    assert [item.plate_number for item in records] == ["沪C12345"]
    database_path.unlink()
    assert not database_path.exists()


def test_config_endpoint_returns_current_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    client = TestClient(create_app())

    response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json()["provider"] == "mock"
    assert response.json()["available_providers"] == ["mock", "local", "ai"]


def test_upload_rejects_non_image_file(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    client = TestClient(create_app())

    response = client.post(
        "/api/recognitions",
        files={"file": ("note.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "仅支持 JPG、PNG、WEBP 图片"


def test_invalid_provider_returns_structured_error(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "invalid")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    client = TestClient(create_app())

    response = client.post(
        "/api/recognitions",
        files={"file": ("car.jpg", b"fake-jpg-content", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "PROVIDER_NOT_FOUND"
    assert response.json()["message"] == "识别模式配置错误"


def test_homepage_serves_static_file_without_500(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "车牌号识别系统" in response.text


def test_homepage_serves_chinese_workbench(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "车牌号识别系统" in response.text
    assert "上传图片" in response.text
    assert "开始识别" in response.text


def _local_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "local")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    return TestClient(create_app())


def test_local_upload_returns_real_provider_result_and_history(tmp_path, monkeypatch):
    client = _local_client(tmp_path, monkeypatch)

    with patch("app.recognizers.local.lpr3.LicensePlateCatcher") as catcher_cls:
        catcher = MagicMock()
        catcher_cls.return_value = catcher
        catcher.return_value = [("粤B12345", 0.92, 2, [10, 20, 200, 80])]
        with patch("app.recognizers.local.cv2.imread", return_value=MagicMock()):
            response = client.post(
                "/api/recognitions",
                files={"file": ("car.png", b"image-content", "image/png")},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["plate_number"] == "粤B12345"
    assert body["confidence"] == 0.92
    assert body["provider"] == "local"
    assert body["status"] == "success"

    history = client.get("/api/recognitions").json()
    assert history[0]["plate_number"] == "粤B12345"
    assert history[0]["provider"] == "local"
    assert history[0]["status"] == "success"


def test_local_upload_persists_explicit_no_match_without_mock_fallback(tmp_path, monkeypatch):
    client = _local_client(tmp_path, monkeypatch)

    with patch("app.recognizers.local.lpr3.LicensePlateCatcher") as catcher_cls:
        catcher = MagicMock()
        catcher_cls.return_value = catcher
        catcher.return_value = []
        with patch("app.recognizers.local.cv2.imread", return_value=MagicMock()):
            response = client.post(
                "/api/recognitions",
                files={"file": ("car.png", b"image-content", "image/png")},
            )

    assert response.status_code == 400
    assert response.json()["code"] == "PLATE_NOT_RECOGNIZED"
    assert response.json()["message"] == "未识别到符合格式的车牌号"

    history = client.get("/api/recognitions").json()
    assert history[0]["plate_number"] == ""
    assert history[0]["confidence"] == 0
    assert history[0]["provider"] == "local"
    assert history[0]["status"] == "failed"
    assert history[0]["error_message"] == "未识别到符合格式的车牌号"


def test_upload_image_returns_result_and_history(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    client = TestClient(create_app())

    response = client.post(
        "/api/recognitions",
        files={"file": ("car.jpg", b"fake-jpg-content", "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["plate_number"]
    assert body["image_url"].startswith("/uploads/")

    history = client.get("/api/recognitions").json()
    assert history[0]["plate_number"] == body["plate_number"]
