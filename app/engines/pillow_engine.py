"""Pillow-backed still-image conversion with bounded pixel decoding."""

from __future__ import annotations

import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from app.engines.registry import ConversionResult


class ImageConversionError(ValueError):
    pass


class PillowImageEngine:
    id = "pillow-image"
    source_formats = ("png", "jpeg", "gif", "webp")
    target_formats = ("png", "jpeg", "webp")
    _encoder = {"png": "PNG", "jpeg": "JPEG", "webp": "WEBP"}
    max_pixels = 40_000_000

    def convert(self, source: bytes, source_format: str, target_format: str) -> ConversionResult:
        if source_format not in self.source_formats or target_format not in self.target_formats:
            raise ImageConversionError("Unsupported image conversion pair")
        Image.MAX_IMAGE_PIXELS = self.max_pixels
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(source)) as opened:
                    if opened.format and opened.format.lower() not in self._accepted_decoder_names(source_format):
                        raise ImageConversionError("Image bytes do not match the detected format")
                    if getattr(opened, "n_frames", 1) != 1:
                        raise ImageConversionError("Animated images are not supported by this conversion")
                    opened.load()
                    image = ImageOps.exif_transpose(opened).copy()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ImageConversionError("Invalid, oversized, or unsupported image") from exc

        if target_format == "jpeg":
            if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
        elif target_format == "png" and image.mode not in ("1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16"):
            image = image.convert("RGBA")

        output = io.BytesIO()
        save_options: dict[str, object] = {}
        if target_format == "jpeg":
            save_options["quality"] = 90
            save_options["optimize"] = True
        elif target_format == "webp":
            save_options["quality"] = 90
            save_options["method"] = 4
        image.save(output, format=self._encoder[target_format], **save_options)
        result = output.getvalue()
        try:
            with Image.open(io.BytesIO(result)) as check:
                check.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise ImageConversionError("Image output failed validation") from exc
        quality = "lossy" if target_format in ("jpeg", "webp") else "lossless"
        notes = ("Metadata is not preserved.",) if image.info else ()
        return ConversionResult(result, target_format, quality, notes)

    @staticmethod
    def _accepted_decoder_names(source_format: str) -> tuple[str, ...]:
        return {"jpeg": ("jpeg", "jpg"), "gif": ("gif",), "png": ("png",), "webp": ("webp",)}[source_format]
