from datetime import datetime, timezone
from pathlib import Path
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


def test_history_repository_counts_records(tmp_path):
    repository = HistoryRepository(tmp_path / "recognitions.db")
    repository.initialize()
    for i in range(5):
        repository.create(
            RecognitionRecord(
                id=0,
                plate_number=f"沪C{i:05d}",
                confidence=0.89,
                provider="mock",
                image_url="/uploads/record.jpg",
                elapsed_ms=15,
                status="success",
                error_message="",
                created_at=datetime(2026, 7, 11, 11, i, tzinfo=timezone.utc),
                message="模拟识别完成",
            )
        )
    assert repository.count() == 5


def test_history_repository_pagination(tmp_path):
    repository = HistoryRepository(tmp_path / "recognitions.db")
    repository.initialize()
    for i in range(25):
        repository.create(
            RecognitionRecord(
                id=0,
                plate_number=f"京A{i:05d}",
                confidence=0.9,
                provider="mock",
                image_url="/uploads/test.jpg",
                elapsed_ms=10,
                status="success",
                error_message="",
                created_at=datetime(2026, 7, 11, 12, i, tzinfo=timezone.utc),
                message="模拟识别完成",
            )
        )

    page1 = repository.list_recent(limit=10, page=1)
    page2 = repository.list_recent(limit=10, page=2)
    page3 = repository.list_recent(limit=10, page=3)

    assert len(page1) == 10
    assert len(page2) == 10
    assert len(page3) == 5
    assert page1[0].plate_number != page2[0].plate_number


def test_history_repository_delete_single(tmp_path):
    repository = HistoryRepository(tmp_path / "recognitions.db")
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

    saved = repository.create(record)
    assert repository.count() == 1

    deleted = repository.delete(saved.id)
    assert deleted is True
    assert repository.count() == 0


def test_history_repository_delete_all(tmp_path):
    repository = HistoryRepository(tmp_path / "recognitions.db")
    repository.initialize()
    for i in range(3):
        repository.create(
            RecognitionRecord(
                id=0,
                plate_number=f"京A{i:05d}",
                confidence=0.9,
                provider="mock",
                image_url="/uploads/test.jpg",
                elapsed_ms=10,
                status="success",
                error_message="",
                created_at=datetime(2026, 7, 11, 12, i, tzinfo=timezone.utc),
                message="模拟识别完成",
            )
        )
    assert repository.count() == 3

    count = repository.delete_all()
    assert count == 3
    assert repository.count() == 0


def test_history_repository_skips_corrupted_rows(tmp_path):
    repository = HistoryRepository(tmp_path / "recognitions.db")
    repository.initialize()
    record = RecognitionRecord(
        id=0,
        plate_number="京A88888",
        confidence=0.95,
        provider="mock",
        image_url="/uploads/test.jpg",
        elapsed_ms=8,
        status="success",
        error_message="",
        created_at=datetime(2026, 7, 11, 10, 0, tzinfo=timezone.utc),
        message="模拟识别完成",
    )
    repository.create(record)

    # Manually insert a corrupted row
    import sqlite3
    conn = sqlite3.connect(tmp_path / "recognitions.db")
    conn.execute(
        "INSERT INTO recognitions (plate_number, confidence, provider, image_url, elapsed_ms, status, error_message, created_at, message) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("corrupt", "not_a_float", "mock", "/uploads/x.jpg", 0, "success", "", "2026-07-11T10:00:00+00:00", "bad"),
    )
    conn.commit()
    conn.close()

    records = repository.list_recent(limit=10)
    assert len(records) == 1
    assert records[0].plate_number == "京A88888"


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


def test_history_list_returns_paginated_response(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    client = TestClient(create_app())

    # Upload to create a record
    client.post(
        "/api/recognitions",
        files={"file": ("car.jpg", b"fake-jpg-content", "image/jpeg")},
    )

    response = client.get("/api/recognitions")
    body = response.json()

    assert response.status_code == 200
    assert "records" in body
    assert "total" in body
    assert "page" in body
    assert "limit" in body
    assert body["total"] >= 1
    assert body["page"] == 1


def test_delete_single_record(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    client = TestClient(create_app())

    # Upload to create a record
    client.post(
        "/api/recognitions",
        files={"file": ("car.jpg", b"fake-jpg-content", "image/jpeg")},
    )

    history = client.get("/api/recognitions").json()
    record_id = history["records"][0]["id"]

    response = client.delete(f"/api/recognitions/{record_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    history_after = client.get("/api/recognitions").json()
    assert history_after["total"] == 0


def test_delete_nonexistent_record_returns_404(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    client = TestClient(create_app())

    response = client.delete("/api/recognitions/99999")
    assert response.status_code == 404


def test_delete_all_records(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    client = TestClient(create_app())

    # Create two records
    client.post("/api/recognitions", files={"file": ("car.jpg", b"fake-1", "image/jpeg")})
    client.post("/api/recognitions", files={"file": ("car2.jpg", b"fake-2", "image/jpeg")})

    assert client.get("/api/recognitions").json()["total"] == 2

    response = client.delete("/api/recognitions")
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2

    assert client.get("/api/recognitions").json()["total"] == 0


def test_history_page_clamps_after_last_record_on_page_is_deleted(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOGNIZER_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recognitions.db'}")
    client = TestClient(create_app())

    for index in range(21):
        client.post(
            "/api/recognitions",
            files={"file": (f"car-{index}.jpg", b"fake-image", "image/jpeg")},
        )

    second_page = client.get("/api/recognitions?limit=20&page=2").json()
    assert len(second_page["records"]) == 1

    client.delete(f"/api/recognitions/{second_page['records'][0]['id']}")
    response = client.get("/api/recognitions?limit=20&page=2")

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert len(response.json()["records"]) == 20


def test_frontend_empty_history_rows_span_every_table_column():
    script = Path("app/static/app.js").read_text(encoding="utf-8")

    assert 'colspan="7"' not in script
    assert script.count('colspan="8"') == 2
    assert "state.historyPage = data.page;" in script


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
    assert body["bbox"] == {"x1": 10, "y1": 20, "x2": 200, "y2": 80}

    history = client.get("/api/recognitions").json()
    assert history["records"][0]["plate_number"] == "粤B12345"
    assert history["records"][0]["provider"] == "local"
    assert history["records"][0]["status"] == "success"
    assert history["records"][0]["bbox"] == {"x1": 10, "y1": 20, "x2": 200, "y2": 80}


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
    assert history["records"][0]["plate_number"] == ""
    assert history["records"][0]["confidence"] == 0
    assert history["records"][0]["provider"] == "local"
    assert history["records"][0]["status"] == "failed"
    assert history["records"][0]["error_message"] == "未识别到符合格式的车牌号"


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
    assert history["records"][0]["plate_number"] == body["plate_number"]
