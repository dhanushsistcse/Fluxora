# Backend Architecture Assessment

## Inspection findings

Inspected the complete `FLUXORA` workspace before implementation. It contains no source files, package/dependency manifests, tests, Docker configuration, frontend, or existing documentation. Therefore there is no existing framework, processing engine, license inventory, or security control to preserve or audit. No components have been replaced.

## Ownership mapping

The requested ownership paths are adopted as-is under `app/`: `backend`, `conversion`, `engines`, `document_tools`, `media_tools`, `security`, `workers`, and `services`. Backend tests live in `tests/backend/`; backend dependency and container configuration live at the repository root; API and security documentation live in `docs/`. No frontend-owned components have been created or modified.

## Implemented baseline

- **API:** FastAPI with Pydantic request/response validation and OpenAPI generation.
- **Conversion core:** format detection, explicit engine registry, capability manifest, declared-pair routing, streamed upload, and bounded image conversion. Detection does not imply conversion support.
- **Execution:** bounded in-process background jobs for image conversions. PDF transformations currently execute synchronously; worker isolation and durable queueing are production requirements.
- **Storage/security:** generated opaque file/job IDs, private storage directory, bearer authentication, single-principal ownership checks, request limits, image output validation, and restricted ZIP extraction primitive. Production requires external identity, malware scanning, sandboxing, quotas, retention cleanup, and private object storage.
- **Engines:** Pillow still-image conversion; pypdf/ReportLab document operations. Other command-line engines are not enabled. Each engine declares formats, operations, requirements, and quality characteristics; undeclared conversion pairs are rejected.

## Initial capability boundary

The implementation exposes health, format/capability discovery, safe upload/inspection, asynchronous image jobs, explicitly registered image conversion, and selected synchronous PDF operations (merge, split, page selection/reordering, watermark, AES-256 password protection, metadata, compression, integrity check, and text-only PDF-to-DOCX). PDF rendering/OCR, DOCX editing and conversion, broader media/archive/ebook/subtitle/font/specialist conversion remain unavailable until adapters are implemented and tested. A registry entry is not itself proof of a usable conversion pair.

## Security review status

There was no preexisting system to audit. New code should use deny-by-default authorization and conversion routing; validate bytes in addition to filenames; prevent path traversal and archive bombs; never interpolate user input into shell commands; limit time/size/concurrency; clean temporary data; and avoid exposing files without owner checks. The starter deployment is not production-ready until worker isolation, persistent storage, external authentication, malware scanning, monitoring, and operational resource controls are configured.

## Dependency/license review

No dependency manifest or vendored package was present. The new manifest uses FastAPI/Uvicorn/Pydantic, Pillow, pypdf, ReportLab, python-docx, cryptography, pytest, and HTTPX with bounded version ranges. These projects have permissive licenses suitable for typical application use (MIT/BSD/Apache-2.0); review transitive dependencies and exact license texts before distribution. The manifest is not a lockfile. Ghostscript, FFmpeg, LibreOffice, OCRmyPDF/Tesseract, qpdf, PyMuPDF, libvips, ExifTool, and 7-Zip are not assumed installed; review their versions, licenses, and deployment implications individually before enabling adapters.

## Next implementation milestones

1. Move synchronous PDF operations into isolated, resource-limited workers and adopt persistent queue/storage.
2. Add malware scanning, retention/cleanup, multi-user identity, and shared rate limiting.
3. Implement remaining engines one by one with API, tests, and explicit capability declarations.
4. Benchmark representative workloads before making performance claims.
