"""Restricted ZIP validation and extraction; no archive path is trusted."""

from __future__ import annotations

import stat
import zipfile
from pathlib import Path, PurePosixPath


class UnsafeArchive(ValueError):
    pass


def safe_extract_zip(
    archive_path: Path,
    destination: Path,
    *,
    max_files: int = 1000,
    max_uncompressed_bytes: int = 512 * 1024 * 1024,
    max_member_bytes: int = 128 * 1024 * 1024,
    max_compression_ratio: int = 200,
) -> list[Path]:
    """Extract regular files only, with traversal, symlink, count and size checks."""
    root = destination.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    extracted: list[Path] = []
    total_written = 0
    try:
        with zipfile.ZipFile(archive_path) as bundle:
            entries = bundle.infolist()
            if len(entries) > max_files:
                raise UnsafeArchive("Archive contains too many entries")
            validated: list[tuple[zipfile.ZipInfo, Path]] = []
            declared_total = 0
            for info in entries:
                name = info.filename
                member = PurePosixPath(name)
                mode = info.external_attr >> 16
                windows_reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
                unsafe_windows_name = any(
                    "\\" in part
                    or ":" in part
                    or part.endswith((" ", "."))
                    or part.rstrip(" .").split(".")[0].upper() in windows_reserved
                    for part in member.parts
                )
                if (
                    not name
                    or "\x00" in name
                    or member.is_absolute()
                    or ".." in member.parts
                    or (member.parts and ":" in member.parts[0])
                    or unsafe_windows_name
                    or stat.S_ISLNK(mode)
                    or info.flag_bits & 0x1
                ):
                    raise UnsafeArchive("Archive contains an unsafe entry")
                target = (root / Path(*member.parts)).resolve()
                if not target.is_relative_to(root):
                    raise UnsafeArchive("Archive entry escapes the extraction directory")
                if info.file_size > max_member_bytes:
                    raise UnsafeArchive("Archive member exceeds size limit")
                if info.file_size and (info.compress_size == 0 or info.file_size / info.compress_size > max_compression_ratio):
                    raise UnsafeArchive("Archive member exceeds compression ratio limit")
                declared_total += info.file_size
                if declared_total > max_uncompressed_bytes:
                    raise UnsafeArchive("Archive exceeds uncompressed size limit")
                validated.append((info, target))

            for info, target in validated:
                if info.is_dir():
                    target.mkdir(mode=0o700, parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                extracted.append(target)
                written = 0
                with bundle.open(info) as source, target.open("xb") as output:
                    while chunk := source.read(1024 * 1024):
                        written += len(chunk)
                        total_written += len(chunk)
                        if written > max_member_bytes or total_written > max_uncompressed_bytes:
                            raise UnsafeArchive("Archive expanded beyond configured limit")
                        output.write(chunk)
                if written != info.file_size:
                    raise UnsafeArchive("Archive member size did not match its directory entry")
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        for path in extracted:
            path.unlink(missing_ok=True)
        raise UnsafeArchive("Invalid or unreadable ZIP archive") from exc
    except UnsafeArchive:
        for path in extracted:
            path.unlink(missing_ok=True)
        raise
    return extracted
