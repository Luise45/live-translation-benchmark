"""
shared data models for the benchmark

purpose:
defines common data structures used across the benchmark, for example
benchmark requests, results, latency values and errors

used by:
- API routes
- benchmark runner
- candidates
- integrations when provider responses are converted into our common format

does not contain:
- provider-specific API responses
- provider API calls
- FE logic
"""

"""
Beispiel erstmal für das Walking Skeleton
"""
from dataclasses import dataclass, field

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


@dataclass
class CandidateResult(TranslationResult):
    """
    Einheitliches Ergebnis, das JEDER Candidate an den Benchmark Runner zurückgibt.

    Erweitert TranslationResult um Infos, die für den Vergleich der Candidates
    gebraucht werden (welcher Candidate, wie lang war das Audio, was hat es gekostet).

    translated_audio enthält eine komplette WAV-Datei als Bytes
    (mono, PCM16, Abtastrate steht in output_sample_rate).
    """
    candidate: str = ""
    model: str | None = None
    input_audio_duration_s: float = 0.0
    output_audio_duration_s: float = 0.0
    output_sample_rate: int = 0
    cost_usd: float | None = None
    # z.B. Infos zur Audio-Konvertierung oder Hinweise zur Kostenberechnung
    metadata: dict = field(default_factory=dict)
