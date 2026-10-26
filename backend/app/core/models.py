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
from dataclasses import dataclass

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