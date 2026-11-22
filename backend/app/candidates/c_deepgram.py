
"""
Deepgram Nova-3 als STT-Benchmark-Kandidat.
"""

from backend.app.core.models import StageResult
from backend.app.integrations.i_deepgram import transcribe_wav


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