"""
Gemeinsame Datenmodelle für den Benchmark.
"""

from dataclasses import dataclass, field


@dataclass
class StageResult:
    stage: str
    model: str
    output: str
    latency_seconds: float
    error: str | None = None


@dataclass
class BenchmarkResult:
    input_audio: str
    steps: list[StageResult] = field(default_factory=list)

    @property
    def total_latency_seconds(self) -> float:
        return sum(step.latency_seconds for step in self.steps)


@dataclass
class TranslationResult:
    provider: str
    architecture: str
    source_language: str
    target_language: str

    source_transcript: str | None
    translated_transcript: str | None
    translated_audio: bytes

    time_to_first_audio_ms: float | None
    total_processing_time_ms: float

@dataclass(frozen=True)
class STTSegment:
    """Ein STT-Abschnitt mit stabiler ID und Zeitangaben."""

    segment_id: int
    text: str
    is_final: bool
    start_seconds: float | None = None
    duration_seconds: float | None = None
    received_at_seconds: float = 0.0
    speech_final: bool = False


@dataclass(frozen=True)
class TranslatedSegment:
    """Übersetzung mit unverändertem ursprünglichem STT-Segment."""

    source: STTSegment
    text: str
    provider: str
    translation_seconds: float
    completed_at_seconds: float


@dataclass(frozen=True)
class SynthesizedSegment:
    """Erzeugtes Audio mit Bezug zum übersetzten Segment."""

    source: TranslatedSegment
    audio: bytes
    audio_format: str
    provider: str
    synthesis_seconds: float
    completed_at_seconds: float   
