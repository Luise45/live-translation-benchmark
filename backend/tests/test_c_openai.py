"""
Tests für candidates/c_openai.py

Prüft die 4 Aufgaben der User Story und die AK – OHNE echten API-Key.
Der OpenAI-Server wird durch einen Fake-WebSocket ersetzt, die echte
i_openai.translate() läuft aber komplett durch.

Ausführen (im Ordner backend/):
    python -m pytest tests/test_c_openai.py -v
"""

import itertools
import json
import queue
import sys
import types
import wave
from pathlib import Path

import numpy as np
import pytest

BACKEND = Path(__file__).resolve().parents[1]
TESTDATA = BACKEND.parent / "testdata"
sys.path.insert(0, str(BACKEND))


# ---------------------------------------------------------------------------
# Fake OpenAI-Server: antwortet wie die echte Realtime-Translate-API
# ---------------------------------------------------------------------------

class FakeOpenAIWebSocket:
    def __init__(self, log):
        self.log = log
        self.q = queue.Queue()
        self.q.put(json.dumps({"type": "session.created"}))
        self.first_chunk = True

    def send(self, message):
        event = json.loads(message)
        self.log.append(event)
        if event["type"] == "session.update":
            self.q.put(json.dumps({"type": "session.updated"}))
        elif event["type"] == "session.input_audio_buffer.append":
            if self.first_chunk:
                self.first_chunk = False
                self.q.put(json.dumps({"type": "session.input_transcript.delta", "delta": " Guten Tag"}))
                self.q.put(json.dumps({"type": "session.output_transcript.delta", "delta": "Good afternoon"}))
            # "übersetztes" Audio = einfach das Eingangs-Audio zurück
            self.q.put(json.dumps({"type": "session.output_audio.delta", "delta": event["audio"]}))
        elif event["type"] == "session.close":
            self.q.put(json.dumps({"type": "session.closed"}))

    def recv(self):
        return self.q.get(timeout=30)

    def close(self):
        pass

    def abort(self):
        pass


def install_fake_websocket(monkeypatch, create_connection):
    """Setzt einen Fake für das websocket-Modul ein, das i_openai benutzt."""
    fake = types.ModuleType("websocket")
    fake.WebSocketException = type("WebSocketException", (Exception,), {})
    fake.create_connection = create_connection
    monkeypatch.setitem(sys.modules, "websocket", fake)  # falls websocket-client fehlt
    from app.integrations import i_openai
    monkeypatch.setattr(i_openai, "websocket", fake)     # falls i_openai schon geladen ist
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    return i_openai


@pytest.fixture
def fake_openai(monkeypatch):
    """Ersetzt das websocket-Modul + API-Key und gibt das Log der gesendeten Events zurück."""
    log = []
    i_openai = install_fake_websocket(monkeypatch, lambda *a, **k: FakeOpenAIWebSocket(log))
    monkeypatch.setattr(i_openai, "CHUNK_FRAMES", 24000)  # 1-s-Chunks
    # kein Echtzeit-Warten: eine "Uhr", die bei jedem Aufruf 1000 s weiterspringt
    fast_clock = itertools.count(step=1000.0)
    monkeypatch.setattr(i_openai, "time", types.SimpleNamespace(perf_counter=lambda: next(fast_clock)))
    return log


def write_wav(path, rate, channels, sampwidth, seconds=1.0, freq=440):
    t = np.arange(int(rate * seconds)) / rate
    mono = 0.5 * np.sin(2 * np.pi * freq * t)
    frames = np.repeat(mono, channels)
    if sampwidth == 2:
        raw = (frames * 32767).astype("<i2").tobytes()
    elif sampwidth == 3:
        ints = (frames * 8388607).astype(np.int32)
        raw = b"".join(int(v).to_bytes(3, "little", signed=True) for v in ints)
    else:
        raise ValueError(sampwidth)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sampwidth)
        w.setframerate(rate)
        w.writeframes(raw)
    return path


# ---------------------------------------------------------------------------
# Aufgabe 1: Audio ins OpenAI-Format
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rate,channels,sampwidth", [
    (48000, 1, 2), (44100, 2, 2), (16000, 1, 2), (44100, 2, 3),
])
def test_audio_wird_zu_24k_mono_pcm16(tmp_path, rate, channels, sampwidth):
    from app.candidates.c_openai import prepare_audio

    src = write_wav(tmp_path / "in.wav", rate, channels, sampwidth)
    out, info = prepare_audio(src, tmp_path)

    with wave.open(str(out)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 24000)
        assert w.getnframes() == pytest.approx(24000, abs=2)  # Dauer bleibt 1 s
        samples = np.frombuffer(w.readframes(w.getnframes()), "<i2") / 32767
    assert info["converted"] is True
    # Ton ist erhalten geblieben (Frequenz 440 Hz, Lautstärke ~0.5)
    peak_hz = np.argmax(np.abs(np.fft.rfft(samples))) * 24000 / len(samples)
    assert peak_hz == pytest.approx(440, abs=2)
    assert samples.max() == pytest.approx(0.5, abs=0.05)


def test_audio_im_richtigen_format_wird_nicht_konvertiert(tmp_path):
    from app.candidates.c_openai import prepare_audio

    src = write_wav(tmp_path / "in.wav", 24000, 1, 2)
    out, info = prepare_audio(src, tmp_path)
    assert out == src and info["converted"] is False


def test_leeres_audio_gibt_fehler(tmp_path):
    from app.candidates.c_openai import prepare_audio

    src = write_wav(tmp_path / "in.wav", 48000, 1, 2, seconds=0)
    with pytest.raises(ValueError):
        prepare_audio(src, tmp_path)


# ---------------------------------------------------------------------------
# Aufgabe 2: Sprachcodes übersetzen
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code,expected", [
    ("de", "de"), ("de-DE", "de"), ("en_US", "en"), ("DEU", "de"),
    ("German", "de"), ("Deutsch", "de"), ("zh-Hans-CN", "zh"), ("pt-BR", "pt"),
])
def test_sprachcodes(code, expected):
    from app.candidates.c_openai import to_openai_language
    assert to_openai_language(code) == expected


@pytest.mark.parametrize("bad", ["", "   ", "klingonisch", "1"])
def test_ungueltige_sprachcodes(bad):
    from app.candidates.c_openai import to_openai_language
    with pytest.raises(ValueError):
        to_openai_language(bad)


def test_nicht_unterstuetzte_zielsprache():
    from app.candidates.c_openai import to_openai_target_language
    with pytest.raises(ValueError, match="not supported"):
        to_openai_target_language("tr")


# ---------------------------------------------------------------------------
# Aufgaben 3 + 4 und AK: Zusammenspiel mit i_openai.py und dem Runner
# ---------------------------------------------------------------------------

def test_candidate_erfuellt_interface():
    from app.candidates.c_openai import OpenAICandidate
    from app.core.interfaces import Candidate

    c = OpenAICandidate()
    assert isinstance(c, Candidate)
    assert (c.name, c.provider, c.architecture) == ("openai_s2s", "openai", "s2s")


def test_candidate_ruft_i_openai_auf_und_liefert_candidate_result(fake_openai, tmp_path):
    from app.candidates.c_openai import OpenAICandidate
    from app.core.models import CandidateResult

    src = write_wav(tmp_path / "in.wav", 48000, 1, 2, seconds=3)
    result = OpenAICandidate().translate(src, "de-DE", "en-US")

    # Aufgabe 3: i_openai hat die richtige Zielsprache an OpenAI geschickt
    update = next(e for e in fake_openai if e["type"] == "session.update")
    assert update["session"]["audio"]["output"]["language"] == "en"
    assert any(e["type"] == "session.input_audio_buffer.append" for e in fake_openai)

    # Aufgabe 4: einheitliches Ergebnis
    assert isinstance(result, CandidateResult)
    assert result.provider == "openai" and result.architecture == "s2s"
    assert result.source_language == "de" and result.target_language == "en"
    assert result.source_transcript == "Guten Tag"
    assert result.translated_transcript == "Good afternoon"
    assert result.translated_audio[:4] == b"RIFF"  # echte WAV-Datei
    assert result.output_sample_rate == 24000
    assert result.input_audio_duration_s == pytest.approx(3.0, abs=0.01)
    assert result.total_processing_time_ms >= 0
    # Kosten: 3 s = 0.05 min * (0.034 + 0.017) USD
    assert result.cost_usd == pytest.approx(0.05 * 0.051, rel=1e-3)


def test_runner_mit_echter_testdatei(fake_openai, tmp_path):
    from app.benchmark.s2s_runner import get_candidates, run_candidate

    src = TESTDATA / "de_Kunde_001_test-mono.wav"  # 48 kHz -> muss konvertiert werden
    candidate = get_candidates()["openai_s2s"]()
    result, wav_path, json_path = run_candidate(candidate, src, "de", "en", tmp_path)

    assert wav_path.is_file() and json_path.is_file()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["candidate"] == "openai_s2s"
    assert data["translated_transcript"] == "Good afternoon"
    assert data["metadata"]["audio_conversion"]["original_sample_rate"] == 48000
    with wave.open(str(wav_path)) as w:
        assert w.getframerate() == 24000


def test_api_fehler_wird_weitergegeben(monkeypatch, tmp_path):
    """Wenn OpenAI einen Fehler schickt, soll der Candidate ihn nicht verschlucken."""
    class ErrorWS(FakeOpenAIWebSocket):
        def __init__(self):
            self.q = queue.Queue()
            self.q.put(json.dumps({"type": "error", "error": {"message": "invalid api key"}}))

    install_fake_websocket(monkeypatch, lambda *a, **k: ErrorWS())

    from app.candidates.c_openai import OpenAICandidate
    src = write_wav(tmp_path / "in.wav", 24000, 1, 2)
    with pytest.raises(RuntimeError, match="invalid api key"):
        OpenAICandidate().translate(src, "de", "en")
