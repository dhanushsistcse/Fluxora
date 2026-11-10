"""Format detection and the explicit, conservative conversion graph."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormatInfo:
    id: str
    mime_type: str
    extensions: tuple[str, ...]
    category: str
    detectable: bool = True


FORMATS: dict[str, FormatInfo] = {
    "pdf": FormatInfo("pdf", "application/pdf", ("pdf",), "document"),
    "docx": FormatInfo("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ("docx",), "document", False),
    "png": FormatInfo("png", "image/png", ("png",), "image"),
    "jpeg": FormatInfo("jpeg", "image/jpeg", ("jpg", "jpeg"), "image"),
    "gif": FormatInfo("gif", "image/gif", ("gif",), "image"),
    "webp": FormatInfo("webp", "image/webp", ("webp",), "image"),
    "zip": FormatInfo("zip", "application/zip", ("zip",), "archive"),
    "mp3": FormatInfo("mp3", "audio/mpeg", ("mp3",), "audio"),
    "wav": FormatInfo("wav", "audio/wav", ("wav",), "audio"),
    "flac": FormatInfo("flac", "audio/flac", ("flac",), "audio"),
    "ogg": FormatInfo("ogg", "application/ogg", ("ogg", "oga", "ogv"), "media"),
    "mp4": FormatInfo("mp4", "video/mp4", ("mp4", "m4v"), "video"),
    "text": FormatInfo("text", "text/plain", ("txt",), "data"),
}


def detect_format(prefix: bytes) -> FormatInfo | None:
    """Detect known formats from content; filename and declared MIME are ignored."""
    if prefix.startswith(b"%PDF-"):
        return FORMATS["pdf"]
    if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return FORMATS["png"]
    if prefix.startswith(b"\xff\xd8\xff"):
        return FORMATS["jpeg"]
    if prefix.startswith((b"GIF87a", b"GIF89a")):
        return FORMATS["gif"]
    if len(prefix) >= 12 and prefix[:4] == b"RIFF" and prefix[8:12] == b"WEBP":
        return FORMATS["webp"]
    if prefix.startswith(b"PK\x03\x04") or prefix.startswith(b"PK\x05\x06"):
        return FORMATS["zip"]
    if prefix.startswith(b"ID3") or (len(prefix) >= 2 and prefix[0] == 0xFF and prefix[1] & 0xE0 == 0xE0):
        return FORMATS["mp3"]
    if len(prefix) >= 12 and prefix[:4] == b"RIFF" and prefix[8:12] == b"WAVE":
        return FORMATS["wav"]
    if prefix.startswith(b"fLaC"):
        return FORMATS["flac"]
    if prefix.startswith(b"OggS"):
        return FORMATS["ogg"]
    if len(prefix) >= 12 and prefix[4:8] == b"ftyp":
        return FORMATS["mp4"]
    if prefix and b"\x00" not in prefix:
        try:
            prefix.decode("utf-8")
        except UnicodeDecodeError:
            return None
        return FORMATS["text"]
    return None


def format_manifest(conversions: dict[str, list[str]]) -> list[dict[str, object]]:
    return [
        {
            "id": fmt.id,
            "mime_type": fmt.mime_type,
            "extensions": list(fmt.extensions),
            "category": fmt.category,
            "detectable": fmt.detectable,
            "convert_to": conversions.get(fmt.id, []),
        }
        for fmt in FORMATS.values()
    ]
