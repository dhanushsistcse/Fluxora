from __future__ import annotations

import io

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from app.backend.main import create_app
from app.security.auth import require_principal
from app.services.jobs import JobManager
from app.services.storage import FileStore


@pytest.fixture
def pdf_api(tmp_path, monkeypatch):
    monkeypatch.setenv("FLUXORA_API_TOKEN", "pdf-test-token")
    jobs = JobManager(max_workers=1)
    app = create_app(store=FileStore(tmp_path), jobs=jobs)
    with TestClient(app) as client:
        yield client, jobs
    jobs.close()


def bearer():
    return {"Authorization": "Bearer pdf-test-token"}


def make_pdf(*labels: str) -> bytes:
    output = io.BytesIO()
    document = canvas.Canvas(output)
    for label in labels:
        document.drawString(72, 720, label)
        document.showPage()
    document.save()
    return output.getvalue()


def upload_pdf(client: TestClient, data: bytes) -> str:
    response = client.post("/api/v1/files", headers=bearer(), files={"file": ("misleading.txt", data, "text/plain")})
    assert response.status_code == 201
    assert response.json()["format"] == "pdf"
    return response.json()["id"]


def operation(client: TestClient, operation_name: str, **fields):
    return client.post("/api/v1/pdf/operations", headers=bearer(), json={"operation": operation_name, **fields})


def test_merge_split_extract_and_reorder(pdf_api):
    client, _ = pdf_api
    first_id = upload_pdf(client, make_pdf("first"))
    second_id = upload_pdf(client, make_pdf("second"))
    merged = operation(client, "merge", file_ids=[first_id, second_id])
    assert merged.status_code == 200
    merged_id = merged.json()["outputs"][0]["id"]
    merged_bytes = client.get(f"/api/v1/files/{merged_id}/download", headers=bearer()).content
    reader = PdfReader(io.BytesIO(merged_bytes))
    assert len(reader.pages) == 2
    assert "first" in reader.pages[0].extract_text()
    assert "second" in reader.pages[1].extract_text()

    split = operation(client, "split", file_id=merged_id)
    assert split.status_code == 200
    assert len(split.json()["outputs"]) == 2
    extracted = operation(client, "extract", file_id=merged_id, pages=[2])
    assert len(PdfReader(io.BytesIO(client.get(extracted.json()["outputs"][0]["download_url"], headers=bearer()).content)).pages) == 1
    reordered = operation(client, "reorder", file_id=merged_id, pages=[2, 1])
    reordered_bytes = client.get(reordered.json()["outputs"][0]["download_url"], headers=bearer()).content
    assert "second" in PdfReader(io.BytesIO(reordered_bytes)).pages[0].extract_text()


def test_watermark_metadata_compression_and_integrity(pdf_api):
    client, _ = pdf_api
    source_id = upload_pdf(client, make_pdf("contract text"))
    watermark = operation(client, "watermark", file_id=source_id, text="AUTHORIZED COPY")
    assert watermark.status_code == 200
    output_id = watermark.json()["outputs"][0]["id"]
    integrity = operation(client, "integrity", file_id=output_id)
    assert integrity.json()["valid"] is True
    assert integrity.json()["pages"] == 1

    metadata = operation(client, "metadata", file_id=output_id, metadata={"Title": "Reviewed"})
    assert metadata.status_code == 200
    compacted = operation(client, "compress", file_id=metadata.json()["outputs"][0]["id"])
    assert compacted.status_code == 200
    compacted_file = client.get(compacted.json()["outputs"][0]["download_url"], headers=bearer())
    assert compacted_file.content.startswith(b"%PDF-")


def test_password_protection_and_text_docx_reconstruction(pdf_api):
    client, _ = pdf_api
    source_id = upload_pdf(client, make_pdf("reconstructed text"))
    protected = operation(client, "protect", file_id=source_id, password="a-strong-test-password")
    assert protected.status_code == 200
    protected_id = protected.json()["outputs"][0]["id"]
    denied = operation(client, "integrity", file_id=protected_id)
    assert denied.status_code == 422
    allowed = operation(client, "integrity", file_id=protected_id, password="a-strong-test-password")
    assert allowed.status_code == 200
    assert allowed.json()["encrypted"] is True

    reconstructed = operation(client, "to-docx", file_id=source_id)
    assert reconstructed.status_code == 200
    output = client.get(reconstructed.json()["outputs"][0]["download_url"], headers=bearer())
    assert output.status_code == 200
    document = Document(io.BytesIO(output.content))
    assert "reconstructed text" in "\n".join(paragraph.text for paragraph in document.paragraphs)


def test_pdf_operation_rejects_non_pdf_and_foreign_owner(pdf_api):
    client, _ = pdf_api
    image = client.post("/api/v1/files", headers=bearer(), files={"file": ("x.png", b"\x89PNG\r\n\x1a\n", "image/png")})
    assert image.status_code == 201
    wrong_type = operation(client, "integrity", file_id=image.json()["id"])
    assert wrong_type.status_code == 415
    source_id = upload_pdf(client, make_pdf("private"))
    client.app.dependency_overrides[require_principal] = lambda: "foreign-owner"
    hidden = operation(client, "integrity", file_id=source_id)
    assert hidden.status_code == 404


def test_malformed_pdf_signature_is_not_treated_as_valid_document(pdf_api):
    client, _ = pdf_api
    source_id = upload_pdf(client, b"%PDF-1.7\nthis is not a PDF structure")
    rejected = operation(client, "integrity", file_id=source_id)
    assert rejected.status_code == 422
