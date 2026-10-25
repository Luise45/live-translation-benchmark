
"""
Benchmark-Runner zum Vergleichen von STT-Modellen.
"""

import time

from backend.app.core.interfaces import STTCandidate
from backend.app.core.models import StageResult


def compare_stt(
    wav_path: str,
    candidates: list[STTCandidate]
) -> list[StageResult]:

    results = []

    for candidate in candidates:
        print(f"Teste: {candidate.name}")

        start = time.perf_counter()

        try:
            result = candidate.transcribe(wav_path)
        except Exception as error:
            result = StageResult(
                stage="stt",
                model=candidate.name,
                output="",
                latency_seconds=time.perf_counter() - start,
                error=str(error)
            )

        results.append(result)

    return results
