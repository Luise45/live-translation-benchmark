from types import SimpleNamespace

import json
import queue
import wave

from app.integrations import i_deepgram_streaming


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
            "speech_final": False,
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
        "DeepLTranslator",
        lambda: SimpleNamespace(translate=fake_translate, close=lambda: None),
    )

    result = i_deepgram_streaming.transcribe_streaming(
        str(audio_path),
        output_path=str(tmp_path / "result.json"),
        target_lang="EN-US",
    )

    assert len(result["interim_results"]) == 1
    assert len(result["final_results"]) == 1

    # Low-latency policy translates stable text before an utterance ends.
    assert result["final_results"][0]["speech_final"] is False
    assert translated_texts == ["Guten Tag"]

    assert result["translation_results"][0][
        "translated_text"
    ] == "Hello"
