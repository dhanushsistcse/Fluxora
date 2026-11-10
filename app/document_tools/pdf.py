"""Bounded PDF transformations built on pypdf and ReportLab."""

from __future__ import annotations

import io
from collections.abc import Mapping, Sequence

from docx import Document
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from reportlab.pdfgen import canvas


MAX_PDF_PAGES = 1000


class DocumentOperationError(ValueError):
    pass


def _reader(data: bytes, password: str | None = None) -> PdfReader:
    try:
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            if not password or not reader.decrypt(password):
                raise DocumentOperationError("PDF is encrypted or password is invalid")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise DocumentOperationError("PDF exceeds the configured page limit")
        return reader
    except (PdfReadError, OSError, ValueError) as exc:
        if isinstance(exc, DocumentOperationError):
            raise
        raise DocumentOperationError("Invalid or unsupported PDF") from exc


def _write(writer: PdfWriter) -> bytes:
    output = io.BytesIO()
    writer.write(output)
    result = output.getvalue()
    if not result.startswith(b"%PDF-"):
        raise DocumentOperationError("PDF output validation failed")
    _reader(result)
    return result


def inspect_pdf(data: bytes, password: str | None = None) -> dict[str, object]:
    reader = _reader(data, password)
    return {"valid": True, "pages": len(reader.pages), "encrypted": reader.is_encrypted}


def merge_pdfs(documents: Sequence[bytes]) -> bytes:
    if not documents or len(documents) > 20:
        raise DocumentOperationError("Provide between 1 and 20 PDF files")
    writer = PdfWriter()
    for data in documents:
        reader = _reader(data)
        for page in reader.pages:
            writer.add_page(page)
            if len(writer.pages) > MAX_PDF_PAGES:
                raise DocumentOperationError("Merged PDF exceeds the configured page limit")
    return _write(writer)


def extract_pages(data: bytes, page_numbers: Sequence[int], password: str | None = None) -> bytes:
    reader = _reader(data, password)
    if not page_numbers or len(page_numbers) > MAX_PDF_PAGES:
        raise DocumentOperationError("At least one page must be selected")
    if len(set(page_numbers)) != len(page_numbers) or any(page < 1 or page > len(reader.pages) for page in page_numbers):
        raise DocumentOperationError("Page numbers must be unique and within the document")
    writer = PdfWriter()
    for page_number in page_numbers:
        writer.add_page(reader.pages[page_number - 1])
    return _write(writer)


def split_pdf(data: bytes, password: str | None = None) -> list[bytes]:
    reader = _reader(data, password)
    return [extract_pages(data, [index + 1], password) for index in range(len(reader.pages))]


def reorder_pages(data: bytes, page_numbers: Sequence[int], password: str | None = None) -> bytes:
    reader = _reader(data, password)
    expected = set(range(1, len(reader.pages) + 1))
    if len(page_numbers) != len(reader.pages) or set(page_numbers) != expected:
        raise DocumentOperationError("Reordering requires every page number exactly once")
    return extract_pages(data, page_numbers, password)


def add_text_watermark(data: bytes, text: str, password: str | None = None) -> bytes:
    if not text or len(text) > 200:
        raise DocumentOperationError("Watermark text must contain 1 to 200 characters")
    reader = _reader(data, password)
    writer = PdfWriter()
    for source_page in reader.pages:
        writer.add_page(source_page)
        page = writer.pages[-1]
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        overlay_stream = io.BytesIO()
        layer = canvas.Canvas(overlay_stream, pagesize=(width, height))
        layer.saveState()
        layer.setFillAlpha(0.20)
        layer.setFillColorRGB(0.35, 0.35, 0.35)
        layer.setFont("Helvetica", min(36, max(12, width / 16)))
        layer.translate(width / 2, height / 2)
        layer.rotate(35)
        layer.drawCentredString(0, 0, text)
        layer.restoreState()
        layer.save()
        overlay_stream.seek(0)
        page.merge_page(PdfReader(overlay_stream).pages[0])
    return _write(writer)


def set_metadata(data: bytes, metadata: Mapping[str, str], password: str | None = None) -> bytes:
    if len(metadata) > 32 or any(len(key) > 64 or len(value) > 1024 for key, value in metadata.items()):
        raise DocumentOperationError("Metadata exceeds field limits")
    reader = _reader(data, password)
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    safe_metadata = {f"/{key.lstrip('/')}": value for key, value in metadata.items()}
    writer.add_metadata(safe_metadata)
    return _write(writer)


def protect_pdf(data: bytes, user_password: str, owner_password: str | None = None) -> bytes:
    if not user_password or len(user_password) > 256:
        raise DocumentOperationError("Password must contain 1 to 256 characters")
    reader = _reader(data)
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    writer.encrypt(user_password=user_password, owner_password=owner_password or user_password, algorithm="AES-256")
    output = io.BytesIO()
    writer.write(output)
    result = output.getvalue()
    protected = PdfReader(io.BytesIO(result), strict=True)
    if not protected.is_encrypted or not protected.decrypt(user_password):
        raise DocumentOperationError("PDF encryption validation failed")
    return result


def compress_pdf(data: bytes, password: str | None = None) -> bytes:
    reader = _reader(data, password)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for page in writer.pages:
        page.compress_content_streams()
    return _write(writer)


def pdf_to_docx(data: bytes, password: str | None = None) -> bytes:
    reader = _reader(data, password)
    document = Document()
    for index, page in enumerate(reader.pages):
        if index:
            document.add_page_break()
        text = page.extract_text() or ""
        for paragraph in text.splitlines():
            document.add_paragraph(paragraph)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()
