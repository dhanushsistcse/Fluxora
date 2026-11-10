"""Engine capability declarations and safe routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ConversionResult:
    data: bytes
    output_format: str
    quality: str
    notes: tuple[str, ...] = ()


class Engine(Protocol):
    id: str
    source_formats: tuple[str, ...]
    target_formats: tuple[str, ...]

    def convert(self, source: bytes, source_format: str, target_format: str) -> ConversionResult: ...


class EngineRegistry:
    def __init__(self) -> None:
        self._engines: list[Engine] = []

    def register(self, engine: Engine) -> None:
        if any(existing.id == engine.id for existing in self._engines):
            raise ValueError(f"Engine already registered: {engine.id}")
        self._engines.append(engine)

    def find(self, source_format: str, target_format: str) -> Engine | None:
        return next(
            (
                engine
                for engine in self._engines
                if source_format in engine.source_formats and target_format in engine.target_formats
            ),
            None,
        )

    def capabilities(self) -> dict[str, list[str]]:
        graph: dict[str, set[str]] = {}
        for engine in self._engines:
            for source in engine.source_formats:
                graph.setdefault(source, set()).update(engine.target_formats)
        return {source: sorted(targets) for source, targets in sorted(graph.items())}

    def manifest(self) -> list[dict[str, object]]:
        return [
            {
                "id": engine.id,
                "source_formats": list(engine.source_formats),
                "target_formats": list(engine.target_formats),
                "operations": ["convert"],
                "enabled": True,
            }
            for engine in self._engines
        ]
