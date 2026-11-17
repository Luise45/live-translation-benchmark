import json
import pytest
import queue
import time
import wave

from backend.app.integrations import i_deepgram_streaming, i_deepl

def test_nur_finalisierte_abschnitte_uebersetzen(
    monkeypatch, tmp_path
):
    """Nur finale Deepgram-Ergebnisse werden mit DeepL übersetzt."""

    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")

    audio_path = tmp_path / "test.wav"

    with wave.open(str(audio_path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 3200)

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

    class FakeDeepLClient:
        def __init__(self, api_key, **kwargs):
            assert api_key == "test-key"

        def translate_text(self, text, *, source_lang, target_lang):
            assert source_lang == "DE"
            assert target_lang == "EN-US"

            translated_texts.append(text)

            class Result:
                text = "Hello"

            return Result()

    monkeypatch.setattr(
        i_deepl.deepl,
        "DeepLClient",
        FakeDeepLClient,
    )

    output_path = tmp_path / "result.json"

    result = i_deepgram_streaming.transcribe_streaming(
        str(audio_path),
        output_path=str(output_path),
        target_lang="EN-US",
    )

    assert len(result["interim_results"]) == 1
    assert len(result["final_results"]) == 1
    assert translated_texts == ["Guten Tag"]

    assert result["transcript"] == "Guten Tag"
    assert result["provider"] == "deepgram"
    assert result["translation_provider"] == "deepl"
    assert result["target_language"] == "EN-US"
    assert result["translated_segments"] == 1

    final_segment = result["final_results"][0]
    translation = result["translation_results"][0]

    assert final_segment["segment_id"] == 1
    assert final_segment["text"] == "Guten Tag"

    assert translation["segment_id"] == final_segment["segment_id"]
    assert translation["original_text"] == final_segment["text"]
    assert translation["translated_text"] == "Hello"
    assert translation["translation_seconds"] >= 0

    assert (
        final_segment["received_at_seconds"]
        <= translation["completed_at_seconds"]
        <= result["total_elapsed_seconds"]
    )

    assert result["input_audio"] == str(audio_path)
    assert result["original_channels"] == 1
    assert result["stream_channels"] == 1
    assert result["sample_rate"] == 16000
    assert result["audio_duration_seconds"] == pytest.approx(0.2)
    assert result["chunk_ms"] == 100
    assert result["chunks_sent"] == 2

    assert result["audio_finished_at_seconds"] is not None
    assert (
        0 <= result["audio_finished_at_seconds"]
        <= result["total_elapsed_seconds"]
    )

    assert output_path.is_file()

    saved_result = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert saved_result == result

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
        i_deepl.deepl,
        "DeepLClient",
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

def test_streaming_speichert_audio_vor_ende_der_eingabe(
    monkeypatch, tmp_path
):
    """Audio wird während der Eingabe gespeichert und korrekt zugeordnet."""

    from pathlib import Path
    from threading import Event

    from backend.app.integrations import i_elevenlabs

    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    monkeypatch.setenv("ELEVEN_API_KEY", "test-key")
    monkeypatch.setenv("VOICE_ID", "test-voice")

    audio_path = tmp_path / "input.wav"
    output_path = tmp_path / "result.json"

    with wave.open(str(audio_path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 3200)

    first_audio_saved = Event()
    input_finished = Event()
    saved_before_input_end = []

    # Das tatsächliche Schreiben bleibt erhalten. Zusätzlich merken wir,
    # ob die Eingabe zum Speicherzeitpunkt noch läuft.
    original_write_bytes = Path.write_bytes

    def observe_write_bytes(path, data):
        written = original_write_bytes(path, data)

        if path.suffix == ".mp3":
            saved_before_input_end.append(
                not input_finished.is_set()
            )
            first_audio_saved.set()

        return written

    monkeypatch.setattr(Path, "write_bytes", observe_write_bytes)

    class FakeWebSocket:
        def __init__(self):
            self.messages = queue.Queue()
            self.chunks_sent = 0

        def settimeout(self, timeout):
            pass

        def send_binary(self, data):
            self.chunks_sent += 1

            if self.chunks_sent == 1:
                for text in ("Hallo", "Welt"):
                    self.messages.put(json.dumps({
                        "type": "Results",
                        "is_final": True,
                        "channel": {
                            "alternatives": [
                                {"transcript": text}
                            ]
                        },
                    }))

            elif self.chunks_sent == 2:
                if not first_audio_saved.wait(timeout=5):
                    raise AssertionError(
                        "Keine MP3-Datei während der Audioeingabe."
                    )

        def send(self, data):
            if json.loads(data).get("type") == "CloseStream":
                input_finished.set()
                self.messages.put(json.dumps({
                    "type": "Metadata",
                    "request_id": "streaming-test",
                }))
                self.messages.put("")

        def recv(self):
            try:
                return self.messages.get(timeout=1)
            except queue.Empty:
                raise (
                    i_deepgram_streaming.websocket
                    .WebSocketTimeoutException()
                )

        def close(self):
            pass

    monkeypatch.setattr(
        i_deepgram_streaming.websocket,
        "create_connection",
        lambda *args, **kwargs: FakeWebSocket(),
    )

    class FakeDeepLClient:
        def __init__(self, api_key, **kwargs):
            assert api_key == "test-key"

        def translate_text(self, text, *, source_lang, target_lang):
            assert source_lang == "DE"
            assert target_lang == "EN-US"

            class Result:
                pass

            result = Result()
            result.text = f"EN: {text}"
            return result

    monkeypatch.setattr(
        i_deepl.deepl,
        "DeepLClient",
        FakeDeepLClient,
    )

    tts_texts = []

    class FakeAudioResponse:
        def __init__(self, audio):
            self.audio = audio

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return self.audio

    def fake_urlopen(request, *, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        text = payload["text"]
        tts_texts.append(text)
        return FakeAudioResponse(text.encode("utf-8"))

    monkeypatch.setattr(
        i_elevenlabs,
        "urlopen",
        fake_urlopen,
    )

    result = i_deepgram_streaming.transcribe_streaming(
        str(audio_path),
        output_path=str(output_path),
        enable_tts=True,
    )

    assert input_finished.is_set()
    assert saved_before_input_end[0] is True
    assert tts_texts == ["EN: Hallo", "EN: Welt"]

    assert result["tts_provider"] == "elevenlabs"
    assert result["synthesized_segments"] == 2
    assert result["request_id"] == "streaming-test"

    audio_results = result["audio_results"]

    assert [item["sequence"] for item in audio_results] == [1, 2]
    assert [item["segment_id"] for item in audio_results] == [1, 2]
    assert [item["translated_text"] for item in audio_results] == [
        "EN: Hallo",
        "EN: Welt",
    ]

    for item, expected_text in zip(
        audio_results,
        ("EN: Hallo", "EN: Welt"),
        strict=True,
    ):
        saved_audio = Path(item["audio_path"])

        assert saved_audio.is_file()
        assert saved_audio.suffix == ".mp3"
        assert saved_audio.read_bytes() == expected_text.encode("utf-8")
        assert item["audio_format"] == "mp3"
        assert item["provider"] == "elevenlabs"
        assert item["synthesis_seconds"] >= 0
        assert (
            item["completed_at_seconds"]
            <= item["available_at_seconds"]
            <= item["saved_at_seconds"]
            <= result["total_elapsed_seconds"]
        )

    assert result["time_to_first_audio_seconds"] == (
        audio_results[0]["available_at_seconds"]
    )

    saved_result = json.loads(
        output_path.read_text(encoding="utf-8")
    )
    assert saved_result == result
