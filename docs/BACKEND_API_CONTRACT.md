# Backend API Contract (v1)

Base path: `/api/v1`. Interactive schema: `/docs`; OpenAPI JSON: `/openapi.json`. All API endpoints except `GET /healthz` require `Authorization: Bearer <FLUXORA_API_TOKEN>`. Authentication is disabled fail-closed: protected routes return 503 until a token is configured. A single configured token identifies one API principal in this starter; production should use real identity and per-user authorization.

## Endpoints

| Method | Path | Purpose | Status |
| --- | --- | --- | --- |
| GET | `/healthz` | Liveness probe | 200 |
| GET | `/api/v1/formats` | Detectable formats and currently enabled conversion targets | 200 |
| GET | `/api/v1/engines` | Enabled engine capability manifest | 200 |
| POST | `/api/v1/pdf/operations` | Run an operation on owned PDF file(s) | 200 |
| POST | `/api/v1/files` | Upload one multipart field named `file`; detected from bytes, not filename | 201 |
| GET | `/api/v1/files/{file_id}` | Inspect an owned upload/output | 200 |
| GET | `/api/v1/files/{file_id}/download` | Download an owned file | 200 |
| POST | `/api/v1/conversions` | Submit a conversion job | 202 |
| GET | `/api/v1/jobs/{job_id}` | Get owned job state/progress | 200 |
| POST | `/api/v1/jobs/{job_id}/cancel` | Request cancellation | 200 |

### Upload

`POST /api/v1/files` consumes `multipart/form-data` with a `file` field. The declared MIME type and original filename are ignored. Uploads are streamed to generated opaque names and limited to 50 MiB by default (`FLUXORA_MAX_UPLOAD_BYTES`). Recognized signatures currently include PDF, PNG, JPEG, GIF, WebP, ZIP, MP3, WAV, FLAC, OGG, MP4, and UTF-8 text. Detection does not assert that a file is structurally valid or processable. Unrecognized signatures return 415; size overflow returns 413.

Response includes `id`, detected `format`, `mime_type`, `category`, `size_bytes`, and an owner-protected `download_url`. Format discovery includes a `detectable` flag; DOCX is output-only because ZIP/DOCX subtype validation is not yet implemented for upload.

### Conversion and jobs

Request body: `{"source_file_id":"<32 lowercase hex>","target_format":"png"}`. The only enabled engine is Pillow for still-image conversion to PNG, JPEG, or WebP from PNG, JPEG, single-frame GIF, and WebP. Actual pairs are reported by `/formats`; all other pairs return 422 and are not advertised. Jobs transition through `queued`, `running`, `succeeded`, `failed`, or `cancelled`; progress is an integer 0–100. A successful response contains `output_file_id`; retrieve its private download URL from its file inspection response. Conversion errors are intentionally generic.

### PDF operations

`POST /api/v1/pdf/operations` accepts an `operation` and file identifier(s). Implemented operations: `merge` (`file_ids`, up to 20 files), `split` (`file_id`, up to 100 pages per request), `extract` (`file_id`, one-based `pages`), `reorder` (`file_id`, full one-based page permutation), `watermark` (`file_id`, `text`), `protect` (`file_id`, `password`, optional `owner_password`), `metadata` (`file_id`, string map `metadata`), `compress` (`file_id`), `integrity` (`file_id`), and `to-docx` (`file_id`). Passwords are optional for reading encrypted input and required in `password` for protection. `to-docx` extracts text into paragraphs/page breaks; it does not reconstruct original layout. Successful transformations return private output file manifests. Integrity returns a report without output. Processing is synchronous in the API process in this starter.

## Error behavior

- 401: missing/invalid bearer token; 429: in-process request limit exceeded; 503: authentication not configured.
- 404: nonexistent or not-owned file/job (ownership is not disclosed).
- 413: upload exceeds configured limit; 415: unsupported file signature; 422: unsupported conversion or malformed request.

## Not implemented yet

DOCX editing/merge/split, PDF rendering, OCR/searchable PDFs, watermark removal, permission controls beyond password encryption, DOCX-to-PDF, media transcoding beyond Pillow still-image conversion, archive routes, remote imports, batch conversion, resumable uploads, persistent job queues, and signed URLs are not available. These must not be presented as supported by a frontend until implemented and verified. API responses and schemas are the integration source of truth.
