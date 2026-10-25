
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
