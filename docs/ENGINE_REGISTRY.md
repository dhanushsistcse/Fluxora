# Engine Registry

The runtime engine registry is deny-by-default. Each engine declares source and target format IDs; `/api/v1/formats` derives the conversion graph from these declarations, and the conversion endpoint rejects pairs without a matching engine. Do not list capabilities based only on an installed executable.

## Enabled and verified

| Engine | Input formats | Output formats | Operation | Limits |
| --- | --- | --- | --- | --- |
| `pillow-image` | PNG, JPEG, GIF, WebP | PNG, JPEG, WebP | Convert still images; validate encoded output | Upload cap 50 MiB by default; 40 million decoded pixels; animated input rejected. JPEG/WebP encoding is lossy; JPEG composites transparency on white. Metadata is not preserved. |

## Enabled document operations

The authenticated `/api/v1/pdf/operations` API uses pypdf and ReportLab for PDF merge, split (capped at 100 outputs/request), page extraction/reordering, text watermarking, AES-256 password protection, metadata writing, content-stream/object compression, and strict parse/page-count integrity checks. PDF-to-DOCX uses python-docx plus pypdf text extraction; it preserves text and page breaks only, not layout, images, tables, or formatting. These are document operations rather than general conversion graph edges. Inputs are capped by the file upload size and 1,000 pages; synchronous processing is not sandboxed and must not be exposed publicly until moved into resource-limited workers.

Source and output are identified/validated using signatures plus Pillow decoding. Capability declarations are in `app/engines/pillow_engine.py` and `app/engines/registry.py`.

## Detected, but no conversion adapter enabled

PDF, ZIP, MP3, WAV, FLAC, OGG, MP4, and UTF-8 text are signature-detected for inspection. ZIP extraction has a restricted helper but no API route. No DOCX editing/merge/split, PDF rendering, OCR, DOCX-to-PDF, watermark removal, audio/video, ebook, subtitle, font, or specialist conversion is currently supported. FFmpeg, FFprobe, libvips, ExifTool, 7-Zip, Ghostscript, LibreOffice, qpdf, OCRmyPDF, and Tesseract are not installed or invoked by this backend.

## Adapter requirements

Every added adapter should declare exact source/target pairs, formats and operations; run in an isolated resource-limited worker; use safe subprocess argument arrays (never shell interpolation); enforce deadlines and cancellation; validate output by content and parser; report quality/metadata behavior; and include malformed-input, resource-limit, and cleanup tests. Review upstream and transitive dependency licenses before enabling it in a distributable product.
