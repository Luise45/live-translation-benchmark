"""
Unit tests for the OpenAI speech-to-speech benchmark candidate.

These tests do not call the OpenAI API. The integration module
app.integrations.i_openai is mocked.

Tests audio-conversion, language codes, result format, error handling
OpenAI-communication is mock.


Test for OpenAi --> test_c_openai_integration.py

"""

import io
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

from app.candidates.c_openai import OpenAICandidate


SAMPLE_RATE = 24000


def _silent_wav_bytes(duration_s: float = 1.0) -> bytes:
    """Erzeugt eine gültige 24-kHz-Mono-PCM16-WAV-Datei im Speicher."""
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        audio.writeframes(b"\x00\x00" * int(SAMPLE_RATE * duration_s))

    return buffer.getvalue()

def _make_translate_mock(translated_audio: bytes):
    """Ersetzt i_openai.translate() im Test.

    Die echte Funktion würde eine WAV-Datei erzeugen. Der Mock tut dasselbe,
    schreibt aber eine lokale Testdatei und ruft OpenAI nicht auf.
    """
    def fake_translate(prepared_path, output_path, target_language):
        output_path.write_bytes(translated_audio)
        return "Guten Tag", "Hello there"

    return fake_translate

@pytest.fixture
def input_audio(tmp_path: Path) -> Path:
    """Erzeugt eine Testeingabedatei mit 48 kHz Stereo-PCM16-Audio."""
    audio_path = tmp_path / "input.wav"
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(48000)
        audio.writeframes(b"\x00\x00" * 2 * 48000)

    audio_path.write_bytes(buffer.getvalue())
    return audio_path


def test_translate_returns_candidate_result(input_audio: Path) -> None:
    translated_audio = _silent_wav_bytes()

    with (
        patch(
            "app.integrations.i_openai.translate",
            side_effect=_make_translate_mock(translated_audio),
        ) as mock_translate,
        patch("app.integrations.i_openai.SAMPLE_RATE", SAMPLE_RATE),
    ):
        candidate = OpenAICandidate()
        result = candidate.translate(
            audio_path=input_audio,
            source_language="de",
            target_language="en",
        )

    mock_translate.assert_called_once()

    args = mock_translate.call_args.args
    prepared_path, output_path, target_language = args

    assert target_language == "en"
    assert prepared_path.name == "input_24k_mono.wav"
    assert output_path.name == "translated.wav"

    assert result.provider == "openai"
    assert result.architecture == "s2s"
    assert result.candidate == "openai_s2s"
    assert result.model == "gpt-realtime-translate"

    assert result.source_language == "de"
    assert result.target_language == "en"
    assert result.source_transcript == "Guten Tag"
    assert result.translated_transcript == "Hello there"

    assert result.translated_audio == translated_audio
    assert result.output_sample_rate == SAMPLE_RATE

    assert result.input_audio_duration_s == pytest.approx(1.0, abs=0.01)
    assert result.output_audio_duration_s == pytest.approx(1.0, abs=0.01)

    assert result.time_to_first_audio_ms is None
    assert result.total_processing_time_ms >= 0.0
    assert result.cost_usd >= 0.0

    assert result.metadata["audio_conversion"]["converted"] is True
    assert result.metadata["requested_source_language"] == "de"
    assert result.metadata["requested_target_language"] == "en"


def test_translate_rejects_missing_audio(tmp_path: Path) -> None:
    missing_audio = tmp_path / "does-not-exist.wav"

    with patch("app.integrations.i_openai.translate") as mock_translate:
        candidate = OpenAICandidate()

        with pytest.raises(FileNotFoundError):
            candidate.translate(
                audio_path=missing_audio,
                source_language="de",
                target_language="en",
            )

    mock_translate.assert_not_called()


def test_translate_rejects_unsupported_target_language(input_audio: Path) -> None:
    with patch("app.integrations.i_openai.translate") as mock_translate:
        candidate = OpenAICandidate()

        with pytest.raises(ValueError, match="not supported"):
            candidate.translate(
                audio_path=input_audio,
                source_language="de",
                target_language="xx",
            )

    mock_translate.assert_not_called()


def test_translate_normalizes_language_codes(input_audio: Path) -> None:
    translated_audio = _silent_wav_bytes()

    with (
        patch(
            "app.integrations.i_openai.translate",
            side_effect=_make_translate_mock(translated_audio),
        ),
        patch("app.integrations.i_openai.SAMPLE_RATE", SAMPLE_RATE),
    ):
        candidate = OpenAICandidate()
        result = candidate.translate(
            audio_path=input_audio,
            source_language="deu",
            target_language="en-US",
        )

    assert result.source_language == "de"
    assert result.target_language == "en"
    assert result.source_transcript == "Guten Tag"
    assert result.translated_transcript == "Hello there"
    assert result.translated_audio == translated_audio
