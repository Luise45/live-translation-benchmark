
import json
import pytest
import queue
import time
import wave

from backend.app.integrations import i_deepgram_streaming


def test_nur_finalisierte_abschnitte_uebersetzen(
    monkeypatch, tmp_path
):
    """Nur finale Deepgram-Ergebnisse werden übersetzt."""

    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")

    # Kurze künstliche WAV-Datei erstellen
    audio_path = tmp_path / "test.wav"

    with wave.open(str(audio_path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 3200)

    # Simulierte Deepgram-Nachrichten
    messages = [
        {
            "type": "Results",
            "is_final": False,
            "channel": {
                "alternatives": [
                    {"transcript": "Guten"}
                ]
            },
        },
        {
            "type": "Results",
            "is_final": True,
            "channel": {
                "alternatives": [
                    {"transcript": "Guten Tag"}
                ]
            },
        },
    ]

    class FakeWebSocket:
        def __init__(self):
            self.messages = queue.Queue()

        def settimeout(self, timeout):
            pass

        def send_binary(self, data):
            pass

        def send(self, data):
            if json.loads(data).get("type") == "CloseStream":
                for message in messages:
                    self.messages.put(json.dumps(message))
                self.messages.put("")

        def recv(self):
            return self.messages.get(timeout=5)

        def close(self):
            pass

    monkeypatch.setattr(
        i_deepgram_streaming.websocket,
        "create_connection",
        lambda *args, **kwargs: FakeWebSocket(),
    )

    translated_texts = []

    def fake_translate(text, target_lang):
        translated_texts.append(text)
        return "Hello"

    monkeypatch.setattr(
        i_deepgram_streaming,
        "translate_text",
        fake_translate,
    )

    result = i_deepgram_streaming.transcribe_streaming(
        str(audio_path),
        output_path=str(tmp_path / "result.json"),
        target_lang="EN-US",
    )

    assert len(result["interim_results"]) == 1
    assert len(result["final_results"]) == 1

    assert translated_texts == ["Guten Tag"]

    assert result["translation_results"][0][
        "translated_text"
    ] == "Hello"

def test_streaming_provider_liefert_segmente(monkeypatch, tmp_path):
    """Der Provider erhält IDs, Reihenfolge und STT-Zeitangaben."""

    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")

    audio_path = tmp_path / "provider_test.wav"

    with wave.open(str(audio_path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 160)

    def make_result(text, is_final, start, duration):
        return {
            "type": "Results",
            "is_final": is_final,
            "speech_final": is_final,
            "start": start,
            "duration": duration,
            "channel": {
                "alternatives": [{"transcript": text}]
            },
        }
    
    messages = [
        make_result("Guten", False, 0.0, 0.1),
        make_result("Guten Tag", True, 0.0, 0.2),
        make_result("Wie geht es dir?", True, 0.2, 0.3),
        {
            "type": "Metadata",
            "request_id": "test-request-123",
        },
    ]

    class FakeWebSocket:
        def __init__(self):
            self.messages = queue.Queue()
            self.sent_audio = []
            self.closed = False

        def settimeout(self, timeout):
            pass

        def send_binary(self, data):
            self.sent_audio.append(data)

        def send(self, data):
            if json.loads(data).get("type") == "CloseStream":
                for message in messages:
                    self.messages.put(json.dumps(message))
                self.messages.put("")

        def recv(self):
            return self.messages.get(timeout=5)

        def close(self):
            self.closed = True

    connection = FakeWebSocket()

    monkeypatch.setattr(
        i_deepgram_streaming.websocket,
        "create_connection",
        lambda *args, **kwargs: connection,
    )

    def unexpected_translation(*args, **kwargs):
        raise AssertionError(
            "Der STT-Provider darf keine Übersetzung aufrufen."
        )

    monkeypatch.setattr(
        i_deepgram_streaming,
        "translate_text",
        unexpected_translation,
    )

    segments = []
    started_at = time.perf_counter()

    provider = i_deepgram_streaming.DeepgramStreamingProvider()
    provider.stream(
        str(audio_path),
        on_segment=segments.append,
        started_at=started_at,
    )

    elapsed = time.perf_counter() - started_at

    assert [segment.text for segment in segments] == [
        "Guten",
        "Guten Tag",
        "Wie geht es dir?",
    ]
    assert [segment.is_final for segment in segments] == [
        False,
        True,
        True,
    ]

    final_segments = [
        segment for segment in segments if segment.is_final
    ]

    assert [segment.segment_id for segment in final_segments] == [1, 2]
    assert [segment.start_seconds for segment in final_segments] == [
        0.0,
        0.2,
    ]
    assert [segment.duration_seconds for segment in final_segments] == [
        0.2,
        0.3,
    ]
    assert all(segment.speech_final for segment in final_segments)

    received_times = [
        segment.received_at_seconds for segment in segments
    ]
    assert received_times == sorted(received_times)
    assert all(0 <= value <= elapsed for value in received_times)

    assert b"".join(connection.sent_audio) == b"\x00\x00" * 160
    assert connection.closed

    metadata = provider.metadata

    assert metadata is not None
    assert metadata.original_channels == 1
    assert metadata.sample_rate == 16000
    assert metadata.audio_duration_seconds == pytest.approx(0.01)
    assert metadata.chunks_sent == 1
    assert metadata.request_id == "test-request-123"

    assert metadata.audio_finished_at_seconds is not None
    assert 0 <= metadata.audio_finished_at_seconds <= elapsed

def test_provider_setzt_alte_metadaten_zurueck(monkeypatch):
    """Auch ein fehlgeschlagener Neustart entfernt alte Sitzungsdaten."""

    provider = i_deepgram_streaming.DeepgramStreamingProvider()
    provider.metadata = i_deepgram_streaming.DeepgramStreamMetadata(
        original_channels=1,
        sample_rate=16000,
        audio_duration_seconds=1.0,
        chunks_sent=10,
        request_id="previous-request",
    )

    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="DEEPGRAM_API_KEY"):
        provider.stream(
            "unused.wav",
            on_segment=lambda segment: None,
            started_at=time.perf_counter(),
        )

    assert provider.metadata is None
