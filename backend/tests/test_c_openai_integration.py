"""
Real OpenAI integration test.

!!!!

This test calls the OpenAI API 

AND

consumes credits.

:)

Run it explicitly only when you want to verify the live integration.
"""

import os
from pathlib import Path

import pytest

from app.candidates.c_openai import OpenAICandidate


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY is not set",
)
def test_openai_real_translation(tmp_path: Path) -> None:
    audio_path = Path("../testdata/de_Kunde_001_test-mono-24k.wav")

    if not audio_path.is_file():
        pytest.skip("Test audio file is not available")

    candidate = OpenAICandidate()
    result = candidate.translate(
        audio_path=audio_path,
        source_language="de",
        target_language="en",
    )

    assert result.candidate == "openai_s2s"
    assert result.target_language == "en"
    assert result.translated_audio
    assert result.translated_audio[:4] == b"RIFF"
