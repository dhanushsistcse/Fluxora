"""FastAPI entry point for the Fluxora backend starter."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.conversion.registry import FORMATS, format_manifest
from app.document_tools.pdf import (
    DocumentOperationError,
    add_text_watermark,
    compress_pdf,
    extract_pages,
    inspect_pdf,
    merge_pdfs,
    pdf_to_docx,
    protect_pdf,
    reorder_pages,
    set_metadata,
    split_pdf,
)
from app.engines.pillow_engine import PillowImageEngine
from app.engines.registry import EngineRegistry
from app.security.audit import audit_event
from app.security.auth import require_principal
from app.services.jobs import JobManager, serialize_job
from app.services.storage import FileStore, UploadRejected


class ConvertRequest(BaseModel):
    source_file_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    target_format: str = Field(pattern=r"^[a-z0-9]{1,16}$")


class PdfOperationRequest(BaseModel):
    operation: Literal["merge", "split", "extract", "reorder", "watermark", "protect", "metadata", "compress", "integrity", "to-docx"]
    file_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    file_ids: list[Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]] = Field(default_factory=list, max_length=20)
    pages: list[int] = Field(default_factory=list, max_length=1000)
    text: str | None = None
    password: str | None = Field(default=None, max_length=256)
    owner_password: str | None = Field(default=None, max_length=256)
    metadata: dict[str, str] = Field(default_factory=dict)


def create_app(
    store: FileStore | None = None,
    jobs: JobManager | None = None,
    engines: EngineRegistry | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Fluxora File Processing API",
        version="0.1.0",
        description="Signature-checked uploads and explicitly registered conversions.",
    )
    app.state.store = store or FileStore()
    app.state.jobs = jobs or JobManager()
    app.state.engines = engines or EngineRegistry()
    if engines is None:
        app.state.engines.register(PillowImageEngine())

    @app.middleware("http")
    async def audit_requests(request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            audit_event(
                "request_failed",
                method=request.method,
                path=request.url.path,
                status_code=500,
                principal_id=getattr(request.state, "principal", None),
            )
            raise
        audit_event(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            principal_id=getattr(request.state, "principal", None),
        )
        return response

    @app.get("/healthz", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/formats", tags=["discovery"])
    def formats(_: str = Depends(require_principal)) -> dict[str, object]:
        return {"formats": format_manifest(app.state.engines.capabilities())}

    @app.get("/api/v1/engines", tags=["discovery"])
    def engines_manifest(_: str = Depends(require_principal)) -> dict[str, object]:
        return {"engines": app.state.engines.manifest()}

    @app.post("/api/v1/pdf/operations", status_code=200, tags=["pdf"])
    def pdf_operation(request: PdfOperationRequest, owner: str = Depends(require_principal)) -> dict[str, object]:
        try:
            if request.operation == "merge":
                if not request.file_ids:
                    raise DocumentOperationError("PDF merge requires file_ids")
                source_records = [_pdf_file(app.state.store, file_id, owner) for file_id in request.file_ids]
                source_data = [record.path.read_bytes() for record in source_records]
                result = merge_pdfs(source_data)
                results = [(result, "pdf")]
                input_size = sum(record.size for record in source_records)
            else:
                if not request.file_id:
                    raise DocumentOperationError("PDF operation requires file_id")
                source_record = _pdf_file(app.state.store, request.file_id, owner)
                source = source_record.path.read_bytes()
                input_size = source_record.size
                if request.operation == "integrity":
                    return {"file_id": request.file_id, **inspect_pdf(source, request.password)}
                if request.operation == "split":
                    page_count = int(inspect_pdf(source, request.password)["pages"])
                    if page_count > 100:
                        raise DocumentOperationError("Split output is limited to 100 pages per request")
                    results = [(data, "pdf") for data in split_pdf(source, request.password)]
                elif request.operation == "extract":
                    results = [(extract_pages(source, request.pages, request.password), "pdf")]
                elif request.operation == "reorder":
                    results = [(reorder_pages(source, request.pages, request.password), "pdf")]
                elif request.operation == "watermark":
                    results = [(add_text_watermark(source, request.text or "", request.password), "pdf")]
                elif request.operation == "protect":
                    results = [(protect_pdf(source, request.password or "", request.owner_password), "pdf")]
                elif request.operation == "metadata":
                    results = [(set_metadata(source, request.metadata, request.password), "pdf")]
                elif request.operation == "compress":
                    results = [(compress_pdf(source, request.password), "pdf")]
                else:
                    results = [(pdf_to_docx(source, request.password), "docx")]

            outputs = [app.state.store.write_output(data, output_format, owner) for data, output_format in results]
            return {
                "operation": request.operation,
                "outputs": [_file_manifest(output) for output in outputs],
                "input_size_bytes": input_size,
                "output_size_bytes": sum(output.size for output in outputs),
            }
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="File not found") from exc
        except (DocumentOperationError, ValueError, OSError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/files", status_code=201, tags=["files"])
    async def upload_file(file: UploadFile = File(...), owner: str = Depends(require_principal)) -> dict[str, object]:
        try:
            record = await app.state.store.accept_upload(file, owner)
        except UploadRejected as exc:
            status = 413 if "size limit" in str(exc) else 415
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        return _file_manifest(record)

    @app.get("/api/v1/files/{file_id}", tags=["files"])
    def inspect_file(file_id: str, owner: str = Depends(require_principal)) -> dict[str, object]:
        record = _owned_file(app.state.store, file_id, owner)
        return _file_manifest(record)

    @app.post("/api/v1/conversions", status_code=202, tags=["conversions"])
    def create_conversion(request: ConvertRequest, response: Response, owner: str = Depends(require_principal)) -> dict[str, object]:
        _owned_file(app.state.store, request.source_file_id, owner)
        try:
            job = app.state.jobs.submit(owner, request.source_file_id, request.target_format, app.state.store, app.state.engines)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        response.headers["Location"] = f"/api/v1/jobs/{job.id}"
        return serialize_job(job)

    @app.get("/api/v1/jobs/{job_id}", tags=["jobs"])
    def get_job(job_id: str, owner: str = Depends(require_principal)) -> dict[str, object]:
        job = _owned_job(app.state.jobs, job_id, owner)
        return serialize_job(job)

    @app.post("/api/v1/jobs/{job_id}/cancel", tags=["jobs"])
    def cancel_job(job_id: str, owner: str = Depends(require_principal)) -> dict[str, object]:
        try:
            job = app.state.jobs.cancel(job_id, owner)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        return serialize_job(job)

    @app.get("/api/v1/files/{file_id}/download", tags=["files"])
    def download_file(file_id: str, owner: str = Depends(require_principal)) -> FileResponse:
        record = _owned_file(app.state.store, file_id, owner)
        info = FORMATS[record.format_id]
        return FileResponse(
            path=record.path,
            media_type=info.mime_type,
            filename=f"{record.id}.{info.extensions[0]}",
            headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
        )

    return app


def _owned_file(store: FileStore, file_id: str, owner: str):
    try:
        return store.get_owned(file_id, owner)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc


def _pdf_file(store: FileStore, file_id: str, owner: str):
    record = _owned_file(store, file_id, owner)
    if record.format_id != "pdf":
        raise HTTPException(status_code=415, detail="Operation requires a PDF file")
    return record


def _owned_job(jobs: JobManager, job_id: str, owner: str):
    try:
        return jobs.get_owned(job_id, owner)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


def _file_manifest(record) -> dict[str, object]:
    info = FORMATS[record.format_id]
    return {
        "id": record.id,
        "format": info.id,
        "mime_type": info.mime_type,
        "category": info.category,
        "size_bytes": record.size,
        "download_url": f"/api/v1/files/{record.id}/download",
    }


app = create_app()
