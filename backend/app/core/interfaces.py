"""
Einheitliche Schnittstellen für Benchmark-Kandidaten und Streaming-Provider.
"""

from collections.abc import Callable
from typing import Protocol

from backend.app.core.models import StageResult, STTSegment


# Bestehende Schnittstellen für dateibasierte Benchmarks


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
        self,
        text: str,
        output_path: str,
    ) -> StageResult:
        ...


# Schnittstellen für die Streaming-Kaskade


class StreamingSTTProvider(Protocol):
    name: str

    def stream(
        self,
        audio_path: str,
        on_segment: Callable[[STTSegment], None],
        *,
        started_at: float,
    ) -> None:
        """Liefert STT-Segmente in Empfangsreihenfolge.

        started_at ist der gemeinsame time.perf_counter()-Startwert.
        received_at_seconds wird relativ zu diesem Wert gemessen.

        on_segment wird für jedes Segment nacheinander aufgerufen.
        Finale Segmente besitzen innerhalb des Streams eindeutige IDs.

        Nach Rückkehr werden keine weiteren Segmente geliefert.
        Fehler werden als Exceptions weitergegeben.
        """
        ...


class TranslationProvider(Protocol):
    name: str

    def translate(
        self,
        text: str,
        *,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Übersetzt einen Text; Fehler werden als Exceptions gemeldet."""
        ...


class TTSProvider(Protocol):
    name: str

    def synthesize(self, text: str) -> bytes:
        """Erzeugt Audiodaten; Fehler werden als Exceptions gemeldet."""
        ...

    @property
    def audio_format(self) -> str:
        """Format der zurückgegebenen Audiodaten, beispielsweise mp3."""
        ...