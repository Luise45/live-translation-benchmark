"""Tests der ElevenLabs-Anbindung ohne Netzwerkzugriff."""

import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from backend.app.integrations import i_elevenlabs


@pytest.fixture
def elevenlabs_env(monkeypatch):
    monkeypatch.setenv("ELEVEN_API_KEY", "test-key")
    monkeypatch.setenv("VOICE_ID", "test-voice")


def test_provider_sendet_text_und_liefert_audio(
    monkeypatch, elevenlabs_env
):
    expected_audio = b"fake-mp3-audio"
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return expected_audio

    def fake_urlopen(request, *, timeout):
        requests.append(request)

        assert request.full_url == (
            "https://api.elevenlabs.io/v1/"
            "text-to-speech/test-voice"
        )
        assert request.get_method() == "POST"
        assert timeout == 120

        headers = {
            key.lower(): value
            for key, value in request.header_items()
        }
        assert headers["xi-api-key"] == "test-key"
        assert headers["content-type"] == "application/json"
        assert headers["accept"] == "audio/mpeg"

        payload = json.loads(request.data.decode("utf-8"))
        assert payload == {
            "text": "Hello",
            "model_id": "eleven_flash_v2_5",
        }

        return FakeResponse()

    monkeypatch.setattr(i_elevenlabs, "urlopen", fake_urlopen)

    provider = i_elevenlabs.ElevenLabsTTSProvider()
    audio = provider.synthesize("Hello")

    assert provider.name == "elevenlabs"
    assert provider.audio_format == "mp3"
    assert audio == expected_audio
    assert len(requests) == 1


def test_bisherige_dateiausgabe_bleibt_erhalten(monkeypatch, tmp_path):
    calls = []

    def fake_synthesize_audio(text):
        calls.append(text)
        return b"fake-mp3-audio"

    monkeypatch.setattr(
        i_elevenlabs,
        "synthesize_audio",
        fake_synthesize_audio,
    )

    output_path = tmp_path / "audio" / "segment.mp3"

    result = i_elevenlabs.synthesize_mp3(
        "Hello",
        str(output_path),
    )

    assert calls == ["Hello"]
    assert result == str(output_path)
    assert output_path.read_bytes() == b"fake-mp3-audio"


def test_leerer_text_startet_keine_anfrage(monkeypatch, elevenlabs_env):
    def unexpected_request(*args, **kwargs):
        pytest.fail("Bei leerem Text darf keine Anfrage erfolgen.")

    monkeypatch.setattr(
        i_elevenlabs,
        "urlopen",
        unexpected_request,
    )

    with pytest.raises(ValueError, match="Text darf nicht leer sein"):
        i_elevenlabs.ElevenLabsTTSProvider().synthesize("   ")


def test_leere_audioantwort_wird_abgelehnt(monkeypatch, elevenlabs_env):
    class EmptyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return b""

    monkeypatch.setattr(
        i_elevenlabs,
        "urlopen",
        lambda *args, **kwargs: EmptyResponse(),
    )

    with pytest.raises(RuntimeError, match="keine Audiodaten"):
        i_elevenlabs.ElevenLabsTTSProvider().synthesize("Hello")


def test_api_fehler_wird_weitergegeben(monkeypatch, elevenlabs_env):
    error_body = json.dumps({
        "detail": {
            "status": "quota_exceeded",
            "message": "Test quota exhausted",
        }
    }).encode("utf-8")

    original_error = HTTPError(
        url="https://api.elevenlabs.io",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=BytesIO(error_body),
    )

    def failing_urlopen(*args, **kwargs):
        raise original_error

    monkeypatch.setattr(
        i_elevenlabs,
        "urlopen",
        failing_urlopen,
    )

    with pytest.raises(RuntimeError, match="HTTP 429") as caught:
        i_elevenlabs.ElevenLabsTTSProvider().synthesize("Hello")

    assert "quota_exceeded" in str(caught.value)
    assert caught.value.__cause__ is original_error