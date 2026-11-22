"""Schnittstellen für vollständige Benchmark-Kandidaten und Einzelstufen."""

from pathlib import Path
from typing import Protocol

from .models import CandidateResult as CandidateResult
from .models import StageResult


class Candidate(Protocol):
    """Gemeinsame Schnittstelle für S2S- und Kaskaden-Kandidaten."""

    name: str
    provider: str
    architecture: str

    def translate(
        self,
        audio_path: Path,
        source_language: str,
        target_language: str,
    ) -> CandidateResult:
        """Verarbeitet eine Audiodatei in einer Übersetzungsrichtung.

        Der Kandidat übernimmt providerspezifische Audioaufbereitung,
        Sprachcodes und Integrationsaufrufe.

        Das Ergebnis enthält übersetztes Audio als vollständige
        WAV-Datei in bytes. Nicht verfügbare Transkripte und die
        unbekannte Zeit bis zur ersten Audioausgabe werden mit
        None angegeben.
        """
        ...


class STTCandidate(Protocol):
    """Schnittstelle für einen einzelnen STT-Schritt."""

    name: str

    def transcribe(self, wav_path: str) -> StageResult:
        ...


class TranslationCandidate(Protocol):
    """Schnittstelle für einen einzelnen Übersetzungsschritt."""

    name: str

    def translate(self, text: str) -> StageResult:
        ...


class TTSCandidate(Protocol):
    """Schnittstelle für einen einzelnen TTS-Schritt mit Dateiausgabe."""

    name: str

    def synthesize(
        self,
        text: str,
        output_path: str,
    ) -> StageResult:
        ...