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

from pathlib import Path
from typing import Protocol

from .models import CandidateResult as CandidateResult


class Candidate(Protocol):
    """Shared interface for benchmark candidates, including S2S and cascades."""

    def translate(
        self,
        audio_path: Path,
        source_language: str,
        target_language: str,
    ) -> CandidateResult:
        """
        Process one audio file in one translation direction.

        The candidate handles provider-specific audio preparation,
        language codes and integration calls.

        Return translated audio as complete WAV file bytes.
        Use None for unavailable transcripts or first-audio latency.
        """
        ...
        """Three dots ... are a Python Ellipsis. In this Interface they pose as placeholders 
        for an intentionally empty method body. here will be defined how to call translate(). 
        A fitting candidate will provide this translate() method, with Eingabe- und Rückgabetyp, 
        concrete implementation is inside that candidate class"""