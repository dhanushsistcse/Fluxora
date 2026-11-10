"""Repeatable local benchmark for the enabled Pillow conversion engine."""

from __future__ import annotations

import argparse
import io
import math
import json
import platform
import statistics
import time

import PIL
from PIL import Image

from app.engines.pillow_engine import PillowImageEngine


def percentile(values: list[float], value: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * value) - 1))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--size", type=int, default=1024)
    args = parser.parse_args()
    if args.iterations < 1 or args.size < 1 or args.size * args.size > PillowImageEngine.max_pixels:
        parser.error("iterations and size must be positive and the image must respect the engine pixel cap")

    image = Image.new("RGB", (args.size, args.size), (32, 96, 160))
    source_buffer = io.BytesIO()
    image.save(source_buffer, format="PNG")
    source = source_buffer.getvalue()
    engine = PillowImageEngine()
    report: dict[str, object] = {
        "python": platform.python_version(),
        "pillow": PIL.__version__,
        "input_format": "png",
        "input_size_bytes": len(source),
        "image_dimensions": [args.size, args.size],
        "iterations": args.iterations,
        "results": {},
    }

    for target in ("jpeg", "webp"):
        durations: list[float] = []
        output_size = 0
        engine.convert(source, "png", target)  # warm-up
        for _ in range(args.iterations):
            started = time.perf_counter()
            output = engine.convert(source, "png", target)
            durations.append(time.perf_counter() - started)
            output_size = len(output.data)
        elapsed = sum(durations)
        report["results"][target] = {
            "p50_seconds": percentile(durations, 0.50),
            "p95_seconds": percentile(durations, 0.95),
            "mean_seconds": statistics.mean(durations),
            "conversions_per_second": args.iterations / elapsed if elapsed else None,
            "output_size_bytes": output_size,
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
