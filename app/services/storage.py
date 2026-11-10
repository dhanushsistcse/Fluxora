"""Private generated-name storage and bounded streaming upload validation."""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile

from app.conversion.registry import FORMATS, detect_format


@dataclass(frozen=True)
class StoredFile:
    id: str
    owner: str
    format_id: str
    size: int
    path: Path
    created_at: float = field(default_factory=time.time)


class UploadRejected(ValueError):
    pass


class FileStore:
    def __init__(
        self,
        root: Path | str | None = None,
        max_upload_bytes: int | None = None,
        retention_seconds: int | None = None,
    ) -> None:
        configured_root = root or os.environ.get("FLUXORA_STORAGE_DIR", "./var/private")
        self.root = Path(configured_root).resolve()
        self.max_upload_bytes = max_upload_bytes if max_upload_bytes is not None else int(os.environ.get("FLUXORA_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
        self.retention_seconds = retention_seconds if retention_seconds is not None else int(os.environ.get("FLUXORA_FILE_RETENTION_SECONDS", "86400"))
        if self.max_upload_bytes < 1 or self.retention_seconds < 0:
            raise ValueError("Upload limit must be positive and retention cannot be negative")
        self.root.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, StoredFile] = {}
        self._lock = threading.RLock()

    def cleanup_expired(self) -> int:
        cutoff = time.time() - self.retention_seconds
        with self._lock:
            expired = [file_id for file_id, record in self._records.items() if record.created_at < cutoff]
            for file_id in expired:
                record = self._records.pop(file_id)
                record.path.unlink(missing_ok=True)
            return len(expired)

    async def accept_upload(self, upload: UploadFile, owner: str) -> StoredFile:
        self.cleanup_expired()
        file_id = uuid.uuid4().hex
        directory = self.root / "files"
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / f"{file_id}.bin"
        total = 0
        prefix = bytearray()
        try:
            with path.open("xb") as output:
                while chunk := await upload.read(1024 * 1024):
                    total += len(chunk)
                    if total > self.max_upload_bytes:
                        raise UploadRejected("Upload exceeds configured size limit")
                    if len(prefix) < 8192:
                        prefix.extend(chunk[: 8192 - len(prefix)])
                    output.write(chunk)
            detected = detect_format(bytes(prefix))
            if detected is None:
                raise UploadRejected("File signature is not recognized")
            record = StoredFile(file_id, owner, detected.id, total, path)
            with self._lock:
                self._records[file_id] = record
            return record
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    def get_owned(self, file_id: str, owner: str) -> StoredFile:
        self.cleanup_expired()
        with self._lock:
            record = self._records.get(file_id)
        if record is None or record.owner != owner:
            raise KeyError(file_id)
        resolved = record.path.resolve()
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise KeyError(file_id)
        return record

    def write_output(self, data: bytes, format_id: str, owner: str) -> StoredFile:
        self.cleanup_expired()
        if format_id not in FORMATS:
            raise ValueError("Unknown output format")
        if len(data) > self.max_upload_bytes:
            raise ValueError("Output exceeds configured size limit")
        file_id = uuid.uuid4().hex
        directory = self.root / "files"
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / f"{file_id}.bin"
        temporary = directory / f".{file_id}.tmp"
        try:
            with temporary.open("xb") as output:
                output.write(data)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        record = StoredFile(file_id, owner, format_id, len(data), path)
        with self._lock:
            self._records[file_id] = record
        return record

    def remove(self, file_id: str, owner: str) -> None:
        record = self.get_owned(file_id, owner)
        record.path.unlink(missing_ok=True)
        with self._lock:
            self._records.pop(file_id, None)
