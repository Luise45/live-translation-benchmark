"""
Mock Speech-to-Speech candidate.

purpose:
Testet den Benchmark-Runner und das Ergebnisformat ohne externe API.

uses:
- core/interfaces.py, core/models.py

does not contain:
- echte Übersetzung
- API-Aufrufe
- Scoring
"""

import time
import wave
from pathlib import Path

from app.core.interfaces import Candidate, CandidateResult


SAMPLE_RATE = 24000
DURATION_S = 1.0


def _silent_wav() -> bytes:
    import io

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        audio.writeframes(b"\x00\x00" * int(SAMPLE_RATE * DURATION_S))
    return buffer.getvalue()


class MockCandidate(Candidate):
    name = "mock_s2s"
    provider = "mock"
    architecture = "s2s"

    def translate(
        self,
        audio_path: Path,
        source_language: str,
        target_language: str,
    ) -> CandidateResult:
        audio_path = Path(audio_path)

        if not audio_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        start = time.perf_counter()

        return CandidateResult(
            provider=self.provider,
            architecture=self.architecture,
            source_language=source_language,
            target_language=target_language,
            source_transcript="[mock] source transcript",
            translated_transcript="[mock] translated transcript",
            translated_audio=_silent_wav(),
            time_to_first_audio_ms=10.0,
            total_processing_time_ms=round((time.perf_counter() - start) * 1000.0, 1),
            candidate=self.name,
            model="mock-model",
            input_audio_duration_s=DURATION_S,
            output_audio_duration_s=DURATION_S,
            output_sample_rate=SAMPLE_RATE,
            cost_usd=0.0,
            metadata={"mock": True},
        )
