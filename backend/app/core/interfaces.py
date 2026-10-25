
"""
Einheitliche Schnittstellen für alle Modellkandidaten.
"""

from typing import Protocol

from backend.app.core.models import StageResult


class STTCandidate(Protocol):
    name: str

    def transcribe(self, wav_path: str) -> StageResult:
        ...


class TranslationCandidate(Protocol):
    name: str

    def translate(self, text: str) -> StageResult:
        ...


class TTSCandidate(Protocol):
    name: str

    def synthesize(
        self, text: str, output_path: str
    ) -> StageResult:
        ...
