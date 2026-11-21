"""Gemeinsame Datenmodelle für den Benchmark."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StageResult:
    """Ergebnis eines einzelnen Verarbeitungsschritts."""

    stage: str
    model: str
    output: str
    latency_seconds: float
    error: str | None = None


@dataclass
class BenchmarkResult:
    """Ergebnisse der bisherigen dateibasierten Kaskade."""

    input_audio: str
    steps: list[StageResult] = field(default_factory=list)

    @property
    def total_latency_seconds(self) -> float:
        return sum(step.latency_seconds for step in self.steps)


@dataclass
class TranslationResult:
    """Gemeinsames Ergebnis einer Sprachübersetzung."""

    provider: str
    architecture: str
    source_language: str
    target_language: str

    source_transcript: str | None
    translated_transcript: str | None
    translated_audio: bytes

    time_to_first_audio_ms: float | None
    total_processing_time_ms: float


@dataclass
class CandidateResult(TranslationResult):
    """Übersetzungsergebnis mit zusätzlichen Benchmark-Angaben."""

    candidate: str
    model: str
    input_audio_duration_s: float
    output_audio_duration_s: float
    output_sample_rate: int
    cost_usd: float
    metadata: dict[str, object]


@dataclass
class BenchmarkCase:
    """Ein Testfall mit Audioeingabe und Sprachrichtung."""

    id: str
    audio_path: Path
    source_language: str
    target_language: str
    reference: str | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class BenchmarkConfig:
    """Konfiguration eines Benchmark-Durchlaufs."""

    candidates: list[str]
    cases: list[BenchmarkCase]
    repetitions: int = 1
    output_dir: Path = Path("results")


@dataclass
class RunRecord:
    """Ergebnis oder Fehler eines einzelnen Kandidaten-Durchlaufs."""

    candidate: str
    case_id: str
    repetition: int
    started_at: str
    runner_wall_time_ms: float
    result: CandidateResult | None
    error: str | None
    audio_file: str | None