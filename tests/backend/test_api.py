from __future__ import annotations

import io
import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.backend.main import create_app
from app.security.auth import require_principal
from app.security.rate_limit import RateLimiter
from app.services.jobs import JobManager
from app.services.storage import FileStore


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("FLUXORA_API_TOKEN", "test-token")
    store = FileStore(tmp_path, max_upload_bytes=2 * 1024 * 1024)
    jobs = JobManager(max_workers=1)
    app = create_app(store=store, jobs=jobs)
    with TestClient(app) as client:
        yield client, jobs
    jobs.close()


def auth(token="test-token"):
    return {"Authorization": f"Bearer {token}"}


def png_bytes() -> bytes:
    image = Image.new("RGB", (12, 8), (12, 90, 200))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_health_is_public_and_protected_routes_require_auth(api):
    client, _ = api
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/api/v1/formats").status_code == 401


def test_audit_logs_events_without_bearer_secret(api, caplog):
    client, _ = api
    caplog.set_level("INFO", logger="fluxora.audit")
    assert client.get("/api/v1/formats", headers=auth()).status_code == 200
    assert "authentication_accepted" in caplog.text
    assert "request_completed" in caplog.text
    assert "test-token" not in caplog.text


def test_upload_uses_signature_not_filename_or_declared_mime(api):
    client, _ = api
    response = client.post(
        "/api/v1/files",
        headers=auth(),
        files={"file": ("../../look-like-a-pdf.pdf", png_bytes(), "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["format"] == "png"
    assert response.json()["mime_type"] == "image/png"


def test_unknown_and_oversized_uploads_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("FLUXORA_API_TOKEN", "test-token")
    jobs = JobManager(max_workers=1)
    app = create_app(store=FileStore(tmp_path, max_upload_bytes=12), jobs=jobs)
    try:
        with TestClient(app) as client:
            bad = client.post("/api/v1/files", headers=auth(), files={"file": ("x.png", b"\x00\xffx", "image/png")})
            assert bad.status_code == 415
            large = client.post("/api/v1/files", headers=auth(), files={"file": ("x.png", png_bytes(), "image/png")})
            assert large.status_code == 413
    finally:
        jobs.close()


def test_conversion_job_validates_output_and_downloads_owned_file(api):
    client, _ = api
    uploaded = client.post("/api/v1/files", headers=auth(), files={"file": ("input.png", png_bytes(), "image/png")})
    file_id = uploaded.json()["id"]
    created = client.post(
        "/api/v1/conversions",
        headers=auth(),
        json={"source_file_id": file_id, "target_format": "jpeg"},
    )
    assert created.status_code == 202
    job_id = created.json()["id"]
    for _ in range(100):
        status = client.get(f"/api/v1/jobs/{job_id}", headers=auth()).json()
        if status["state"] in {"succeeded", "failed"}:
            break
        time.sleep(0.01)
    assert status["state"] == "succeeded"
    assert status["progress"] == 100
    output_id = status["output_file_id"]
    downloaded = client.get(f"/api/v1/files/{output_id}/download", headers=auth())
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"\xff\xd8\xff")


def test_unsupported_pairs_are_not_routed(api):
    client, _ = api
    uploaded = client.post("/api/v1/files", headers=auth(), files={"file": ("document.pdf", b"%PDF-1.7\nminimal", "application/pdf")})
    assert uploaded.status_code == 201
    response = client.post(
        "/api/v1/conversions",
        headers=auth(),
        json={"source_file_id": uploaded.json()["id"], "target_format": "png"},
    )
    assert response.status_code == 422
    manifest = client.get("/api/v1/formats", headers=auth()).json()["formats"]
    pdf = next(item for item in manifest if item["id"] == "pdf")
    assert pdf["convert_to"] == []


def test_foreign_principal_cannot_inspect_or_download_file(api):
    client, _ = api
    uploaded = client.post("/api/v1/files", headers=auth(), files={"file": ("x.png", png_bytes(), "image/png")})
    file_id = uploaded.json()["id"]
    client.app.dependency_overrides[require_principal] = lambda: "another-principal"
    assert client.get(f"/api/v1/files/{file_id}", headers=auth()).status_code == 404
    assert client.get(f"/api/v1/files/{file_id}/download", headers=auth()).status_code == 404


def test_format_discovery_reports_only_registered_image_routes(api):
    client, _ = api
    formats = client.get("/api/v1/formats", headers=auth()).json()["formats"]
    png = next(item for item in formats if item["id"] == "png")
    assert set(png["convert_to"]) == {"jpeg", "png", "webp"}
    detected_only = next(item for item in formats if item["id"] == "mp4")
    assert detected_only["convert_to"] == []


def test_sliding_window_limiter_rejects_excess_requests():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("principal")
    assert limiter.allow("principal")
    assert not limiter.allow("principal")
    assert limiter.allow("another-principal")


def test_file_retention_cleanup_removes_expired_generated_files(tmp_path):
    store = FileStore(tmp_path, retention_seconds=1)
    record = store.write_output(b"safe", "text", "owner")
    store._records[record.id] = replace(record, created_at=time.time() - 2)
    assert store.cleanup_expired() == 1
    assert not record.path.exists()
