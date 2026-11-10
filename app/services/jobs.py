"""Bounded asynchronous job execution and ownership-aware job state."""

from __future__ import annotations

import os
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from app.conversion.registry import detect_format
from app.engines.registry import EngineRegistry
from app.services.storage import FileStore


@dataclass
class Job:
    id: str
    owner: str
    source_file_id: str
    target_format: str
    state: str = "queued"
    progress: int = 0
    output_file_id: str | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    _created_epoch: float = field(default_factory=time.time, repr=False)
    _future: Future[None] | None = field(default=None, repr=False)


class JobManager:
    def __init__(self, max_workers: int | None = None, retention_seconds: int = 86400) -> None:
        workers = max_workers or int(os.environ.get("FLUXORA_MAX_WORKERS", "2"))
        if retention_seconds < 0:
            raise ValueError("Job retention cannot be negative")
        self.retention_seconds = retention_seconds
        self._executor = ThreadPoolExecutor(max_workers=max(1, min(workers, 4)), thread_name_prefix="fluxora-worker")
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()

    def submit(self, owner: str, source_file_id: str, target_format: str, store: FileStore, engines: EngineRegistry) -> Job:
        source = store.get_owned(source_file_id, owner)
        engine = engines.find(source.format_id, target_format)
        if engine is None:
            raise ValueError(f"Unsupported conversion: {source.format_id} to {target_format}")
        job = Job(uuid.uuid4().hex, owner, source_file_id, target_format)
        with self._lock:
            self._cleanup_locked()
            self._jobs[job.id] = job
        job._future = self._executor.submit(self._run, job, source.path, store, engine)
        return job

    def _run(self, job: Job, source_path, store: FileStore, engine) -> None:
        with self._lock:
            if job.state == "cancelled":
                return
            job.state = "running"
            job.progress = 10
        try:
            source = source_path.read_bytes()
            with self._lock:
                job.progress = 30
            result = engine.convert(source, detect_format(source[:8192]).id, job.target_format)
            with self._lock:
                job.progress = 85
            detected = detect_format(result.data[:8192])
            if detected is None or detected.id != job.target_format or result.output_format != job.target_format:
                raise ValueError("Engine output validation failed")
            output = store.write_output(result.data, result.output_format, job.owner)
            with self._lock:
                if job.state != "cancelled":
                    job.output_file_id = output.id
                    job.state = "succeeded"
                    job.progress = 100
                else:
                    store.remove(output.id, job.owner)
        except Exception:
            with self._lock:
                if job.state != "cancelled":
                    job.state = "failed"
                    job.error = "Conversion failed; input may be invalid or unsupported"

    def get_owned(self, job_id: str, owner: str) -> Job:
        with self._lock:
            self._cleanup_locked()
            job = self._jobs.get(job_id)
            if job is None or job.owner != owner:
                raise KeyError(job_id)
            return job

    def _cleanup_locked(self) -> None:
        cutoff = time.time() - self.retention_seconds
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.state in ("succeeded", "failed", "cancelled") and job._created_epoch < cutoff
        ]
        for job_id in expired:
            self._jobs.pop(job_id, None)

    def cancel(self, job_id: str, owner: str) -> Job:
        with self._lock:
            job = self.get_owned(job_id, owner)
            if job.state in ("succeeded", "failed", "cancelled"):
                return job
            if job._future and job._future.cancel():
                job.state = "cancelled"
                job.progress = 0
            else:
                job.state = "cancelled"
            return job

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


def serialize_job(job: Job) -> dict[str, object]:
    return {
        "id": job.id,
        "state": job.state,
        "progress": job.progress,
        "source_file_id": job.source_file_id,
        "target_format": job.target_format,
        "output_file_id": job.output_file_id,
        "error": job.error,
        "created_at": job.created_at,
    }
