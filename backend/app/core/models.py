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
from pathlib import Path

"""required running order
TranslationResult
CandidateResult
BenchmarkCase
BenchmarkConfig
RunRecord
"""

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
    candidate: str
    model: str
    input_audio_duration_s: float
    output_audio_duration_s: float
    output_sample_rate: int
    cost_usd: float
    metadata: dict[str, object]

@dataclass 
class BenchmarkCase: #Name der class nicht TestCase, denn: in pytest Klassen mit Test… einsammeln/warnen
    id: str
    audio_path: Path
    source_language: str
    target_language: str
    reference: str | None = None #fuer spaeteres scoring
    tags: dict[str,str] = field(default_factory=dict) # z.B. noise, scenario

@dataclass
class BenchmarkConfig:
    candidates: list[str]
    cases: list[BenchmarkCase]
    repetitions: int = 1
    output_dir: Path = Path("results")

@dataclass
class RunRecord:
    candidate: str
    case_id: str
    repetition: str
    started_at: str
    runner_wall_time_ms: float
    result: CandidateResult | None
    error: str | None
    audio_file: str | None

    