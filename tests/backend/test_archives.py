from __future__ import annotations

import zipfile

import pytest

from app.security.archives import UnsafeArchive, safe_extract_zip


def test_zip_traversal_is_rejected_and_does_not_write_outside(tmp_path):
    archive = tmp_path / "traversal.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../outside.txt", "nope")
    destination = tmp_path / "out"
    with pytest.raises(UnsafeArchive):
        safe_extract_zip(archive, destination)
    assert not (tmp_path / "outside.txt").exists()


def test_archive_expansion_limit_is_enforced(tmp_path):
    archive = tmp_path / "large.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("large.txt", "A" * 10000)
    with pytest.raises(UnsafeArchive):
        safe_extract_zip(archive, tmp_path / "out", max_uncompressed_bytes=100)


def test_valid_zip_extracts_only_expected_content(tmp_path):
    archive = tmp_path / "valid.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("folder/file.txt", "safe content")
    extracted = safe_extract_zip(archive, tmp_path / "out")
    assert len(extracted) == 1
    assert extracted[0].read_text() == "safe content"


@pytest.mark.parametrize("member", [r"..\outside.txt", "CON.txt", "nested/COM1.log", "file.txt:stream"])
def test_windows_special_paths_are_rejected(tmp_path, member):
    archive = tmp_path / "windows-path.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(member, "blocked")
    with pytest.raises(UnsafeArchive):
        safe_extract_zip(archive, tmp_path / "out")
