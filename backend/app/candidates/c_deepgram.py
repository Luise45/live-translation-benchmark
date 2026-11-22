
"""
Deepgram Nova-3 als STT-Benchmark-Kandidat.
"""

from app.core.models import StageResult
from app.integrations.i_deepgram import transcribe_wav


class DeepgramSTT:
    name = "deepgram_nova3"

    def transcribe(self, wav_path: str) -> StageResult:

        transcript, latency = transcribe_wav(wav_path)

        return StageResult(
            stage="stt",
            model=self.name,
            output=transcript,
            latency_seconds=latency
        )