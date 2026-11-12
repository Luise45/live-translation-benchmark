"""
shared interfaces for all benchmark candidates.

purpose:
defines what every benchmark candidate must provide so the benchmark runner
can use all candidates in the same way.

used by:
- benchmark/runner.py
- candidate implementations

does not contain:
- provider API calls
- provider-specific response formats
- benchmark scoring
"""

from abc import ABC, abstractmethod
from pathlib import Path

from app.core.models import CandidateResult

__all__ = ["Candidate", "CandidateResult"]


class Candidate(ABC):
    """
    Basisklasse für alle Benchmark-Candidates.

    Der Runner kennt nur diese Schnittstelle: Er gibt eine WAV-Datei plus
    Sprachcodes hinein und bekommt immer ein CandidateResult zurück –
    egal welcher Anbieter dahinter steckt.

    Sprachcodes kommen im Benchmark-Format an (z.B. "de", "de-DE", "en_US").
    Jeder Candidate übersetzt sie selbst in das Format seines Anbieters.

    Fehler (falsches Audio, API-Fehler, ...) werden als Exception geworfen;
    der Runner fängt sie ab und protokolliert sie.
    """

    #: eindeutiger Name im Benchmark, z.B. "openai_s2s"
    name: str
    #: Anbieter, z.B. "openai"
    provider: str
    #: "s2s" (Speech-to-Speech) oder "cascade" (STT -> MT -> TTS)
    architecture: str

    @abstractmethod
    def translate(
        self,
        audio_path: Path,
        source_language: str,
        target_language: str,
    ) -> CandidateResult:
        """Übersetzt die Audiodatei und gibt das einheitliche Ergebnis zurück."""
