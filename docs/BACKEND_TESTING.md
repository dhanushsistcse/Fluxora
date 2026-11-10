# Backend Testing and Verification

## Commands

- Install dependencies from `requirements.txt` in a virtual environment.
- Run all backend tests with `pytest -q tests/backend`.
- Run the repeatable image microbenchmark from the repository root with `python -m benchmarks.benchmark_image_conversion --iterations 20 --size 1024`.
- Start locally with Uvicorn using `app.backend.main:app`; set `FLUXORA_API_TOKEN` to a long random secret and use a private `FLUXORA_STORAGE_DIR`.

## Automated coverage

The backend suite covers content-signature detection despite false filename/MIME, unknown and oversized uploads, conversion capability rejection, image conversion and output signature validation, file ownership, authentication, ZIP traversal/expansion restrictions, PDF merge/split/extract/reorder, watermarking, metadata, compression, integrity validation, AES-256 protection, and text-to-DOCX reconstruction. Tests use generated fixtures and temporary storage.

## Benchmark sample

Executed on Windows, CPython 3.14.7, Pillow 12.3.0, using a generated solid-color 1024×1024 RGB PNG (5,338 input bytes), 1 warm-up plus 10 timed conversions per target. PNG→JPEG: p50 7.05 ms, p95 9.88 ms, mean 7.45 ms, 134.2 conversions/s, 6,430 output bytes. PNG→WebP: p50 61.96 ms, p95 64.79 ms, mean 62.62 ms, 16.0 conversions/s, 1,950 output bytes. This highly compressible synthetic image and single-process run are a smoke benchmark only, not a production capacity estimate; repeat with representative photos and concurrent worker/API load. Memory was not measured.

## Current limitations

The suite does not establish sandbox isolation, malware-scanner integration, production rate limits, cancellation of an already-running conversion, process restart durability, or full resource quotas. Add worker-level integration and stress tests before production. Benchmark representative safe fixtures and report throughput, peak RAM, CPU, and p50/p95 latency with machine and dependency versions.
