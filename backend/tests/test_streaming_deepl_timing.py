
import json
import queue
import time
import wave

from backend.app.integrations import i_deepgram_streaming


def test_uebersetzung_waehrend_audio(monkeypatch, tmp_path):
    """Prüft Streaming, Reihenfolge und nicht blockierende Übersetzung."""

    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")

    # 1,5 Sekunden künstliches Audio erzeugen
    audio_path = tmp_path / "test.wav"

    with wave.open(str(audio_path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 24000)

    class FakeWebSocket:
        def __init__(self):
            self.messages = queue.Queue()
            self.chunks = 0
            self.close_requested = False

        def settimeout(self, timeout):
            pass

        def send_binary(self, data):
            self.chunks += 1

            # Bereits während des Sendens Ergebnisse liefern
            if self.chunks in (2, 3):
                text = (
                    "Guten Tag"
                    if self.chunks == 2
                    else "Wie geht es Ihnen?"
                )

                self.messages.put(json.dumps({
                    "type": "Results",
                    "is_final": True,
                    "channel": {
                        "alternatives": [
                            {"transcript": text}
                        ]
                    },
                }))

        def send(self, data):
            if json.loads(data).get("type") == "CloseStream":
                self.close_requested = True

        def recv(self):
            try:
                return self.messages.get(timeout=0.05)
            except queue.Empty:
                if self.close_requested:
                    time.sleep(0.05)
                    return ""
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

    def fake_translate(text, target_lang):
        assert target_lang == "EN-US"

        # Erste Übersetzung künstlich verlangsamen
        if text == "Guten Tag":
            time.sleep(0.35)
            return "Hello"

        return "How are you?"

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

    segments = result["final_results"]
    translations = result["translation_results"]

    # Beide Abschnitte wurden übersetzt
    assert len(segments) == 2
    assert len(translations) == 2

    # Reihenfolge und Zuordnung stimmen
    assert [t["segment_id"] for t in translations] == [1, 2]
    assert [t["translated_text"] for t in translations] == [
        "Hello",
        "How are you?",
    ]

    # Zweiter Abschnitt trifft ein, während DeepL
    # den ersten Abschnitt noch übersetzt
    assert (
        segments[1]["received_at_seconds"]
        < translations[0]["completed_at_seconds"]
    )

    # Erste Übersetzung ist vor Audioende fertig
    assert (
        translations[0]["completed_at_seconds"]
        < result["audio_finished_at_seconds"]
    )

    # Übersetzungszeiten wurden erfasst
    assert all(
        t["translation_seconds"] >= 0
        for t in translations
    )
