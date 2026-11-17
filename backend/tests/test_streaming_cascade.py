"""Tests der Streaming-Kaskade ohne externe Provider."""

from threading import Event

import pytest

from backend.app.benchmark.streaming_cascade import (
    run_streaming_cascade,
)
from backend.app.core.models import STTSegment


class FakeSTTProvider:
    name = "fake-stt"

    def __init__(self, segments):
        self.segments = segments

    def stream(self, audio_path, on_segment, *, started_at):
        for segment in self.segments:
            on_segment(segment)


class FakeTranslationProvider:
    def __init__(self, name="fake-translation", prefix="EN"):
        self.name = name
        self.prefix = prefix
        self.calls = []

    def translate(self, text, *, source_lang, target_lang):
        self.calls.append((text, source_lang, target_lang))
        return f"{self.prefix}: {text}"


def test_finale_segmente_behalten_reihenfolge_und_daten():
    interim = STTSegment(
        segment_id=1,
        text="Guten",
        is_final=False,
    )
    first = STTSegment(
        segment_id=10,
        text="Guten Tag",
        is_final=True,
        start_seconds=0.0,
        duration_seconds=1.2,
        received_at_seconds=0.0,
        speech_final=True,
    )
    empty = STTSegment(
        segment_id=11,
        text="   ",
        is_final=True,
    )
    second = STTSegment(
        segment_id=20,
        text="Wie geht es dir?",
        is_final=True,
        start_seconds=1.2,
        duration_seconds=1.5,
    )
    translator = FakeTranslationProvider()

    results = run_streaming_cascade(
        "test.wav",
        stt_provider=FakeSTTProvider(
            [interim, first, empty, second]
        ),
        translation_provider=translator,
        source_lang="DE",
        target_lang="EN-US",
    )

    assert translator.calls == [
        ("Guten Tag", "DE", "EN-US"),
        ("Wie geht es dir?", "DE", "EN-US"),
    ]
    assert [result.source.segment_id for result in results] == [10, 20]
    assert results[0].source is first
    assert results[1].source is second
    assert [result.text for result in results] == [
        "EN: Guten Tag",
        "EN: Wie geht es dir?",
    ]

    for result in results:
        assert result.translation_seconds >= 0
        assert result.completed_at_seconds >= result.translation_seconds

    assert (
        results[1].completed_at_seconds
        >= results[0].completed_at_seconds
    )


def test_uebersetzung_laeuft_waehrend_des_stt_streams():
    translation_started = Event()
    second_segment_received = Event()

    class StreamingSTT:
        name = "streaming-test"

        def stream(self, audio_path, on_segment, *, started_at):
            on_segment(
                STTSegment(
                    segment_id=1,
                    text="Hallo",
                    is_final=True,
                )
            )

            if not translation_started.wait(timeout=5):
                raise AssertionError(
                    "Übersetzung startet nicht während des Streams."
                )

            on_segment(
                STTSegment(
                    segment_id=2,
                    text="Welt",
                    is_final=True,
                )
            )
            second_segment_received.set()

    class WaitingTranslator:
        name = "waiting-test"

        def translate(self, text, *, source_lang, target_lang):
            translation_started.set()

            if not second_segment_received.wait(timeout=5):
                raise AssertionError(
                    "Die Übersetzung blockiert den STT-Empfang."
                )

            return f"EN: {text}"

    results = run_streaming_cascade(
        "test.wav",
        stt_provider=StreamingSTT(),
        translation_provider=WaitingTranslator(),
    )

    assert [result.source.segment_id for result in results] == [1, 2]


@pytest.mark.parametrize(
    ("provider_name", "prefix"),
    [
        ("provider-a", "A"),
        ("provider-b", "B"),
    ],
)
def test_uebersetzungsprovider_ist_austauschbar(provider_name, prefix):
    segment = STTSegment(
        segment_id=1,
        text="Hallo",
        is_final=True,
    )
    translator = FakeTranslationProvider(
        name=provider_name,
        prefix=prefix,
    )

    results = run_streaming_cascade(
        "test.wav",
        stt_provider=FakeSTTProvider([segment]),
        translation_provider=translator,
    )

    assert results[0].provider == provider_name
    assert results[0].text == f"{prefix}: Hallo"


def test_uebersetzungsfehler_wird_weitergegeben():
    original_error = ValueError("Testfehler")

    class FailingTranslator:
        name = "failing-test"

        def translate(self, text, *, source_lang, target_lang):
            raise original_error

    with pytest.raises(RuntimeError) as caught:
        run_streaming_cascade(
            "test.wav",
            stt_provider=FakeSTTProvider(
                [STTSegment(1, "Hallo", True)]
            ),
            translation_provider=FailingTranslator(),
        )

    assert caught.value.__cause__ is original_error


def test_stt_fehler_wird_weitergegeben():
    original_error = ValueError("STT-Testfehler")

    class FailingSTT:
        name = "failing-stt"

        def stream(self, audio_path, on_segment, *, started_at):
            raise original_error

    with pytest.raises(ValueError) as caught:
        run_streaming_cascade(
            "test.wav",
            stt_provider=FailingSTT(),
            translation_provider=FakeTranslationProvider(),
        )

    assert caught.value is original_error


def test_leerer_stream_liefert_keine_uebersetzungen():
    translator = FakeTranslationProvider()

    results = run_streaming_cascade(
        "test.wav",
        stt_provider=FakeSTTProvider([]),
        translation_provider=translator,
    )

    assert results == []
    assert translator.calls == []


def test_beobachter_erhaelt_auch_vorlaeufige_segmente():
    """Alle Segmente werden gemeldet, aber nur finale übersetzt."""

    interim = STTSegment(
        segment_id=1,
        text="Guten",
        is_final=False,
    )
    final = STTSegment(
        segment_id=1,
        text="Guten Tag",
        is_final=True,
    )

    observed_segments = []
    translator = FakeTranslationProvider()

    results = run_streaming_cascade(
        "test.wav",
        stt_provider=FakeSTTProvider([interim, final]),
        translation_provider=translator,
        on_segment=observed_segments.append,
    )

    assert observed_segments == [interim, final]
    assert translator.calls == [
        ("Guten Tag", "DE", "EN-US"),
    ]
    assert len(results) == 1
    assert results[0].source is final


def test_kaskade_verwendet_gemeinsame_zeitbasis(monkeypatch):
    """STT und Übersetzung beziehen sich auf denselben Startwert."""

    from backend.app.benchmark import streaming_cascade

    # Eine feste Uhr macht den Test unabhängig von der Rechnergeschwindigkeit.
    monkeypatch.setattr(
        streaming_cascade.time,
        "perf_counter",
        lambda: 105.0,
    )

    received_start_values = []

    class RecordingSTT:
        name = "recording-stt"

        def stream(self, audio_path, on_segment, *, started_at):
            received_start_values.append(started_at)

            on_segment(
                STTSegment(
                    segment_id=7,
                    text="Hallo",
                    is_final=True,
                    received_at_seconds=(
                        streaming_cascade.time.perf_counter()
                        - started_at
                    ),
                )
            )

    results = run_streaming_cascade(
        "test.wav",
        stt_provider=RecordingSTT(),
        translation_provider=FakeTranslationProvider(),
        started_at=100.0,
    )

    assert received_start_values == [100.0]
    assert len(results) == 1

    result = results[0]
    assert result.source.segment_id == 7
    assert result.source.received_at_seconds == 5.0
    assert result.completed_at_seconds == 5.0
    assert result.translation_seconds == 0.0

@pytest.mark.parametrize(
    ("provider_name", "audio_format", "audio_data"),
    [
        ("tts-a", "mp3", b"audio-a"),
        ("tts-b", "wav", b"audio-b"),
    ],
)
def test_tts_provider_ist_austauschbar(
    provider_name, audio_format, audio_data
):
    """TTS erhält Übersetzungen; Audio bleibt den Segmenten zugeordnet."""

    class FakeTTS:
        def __init__(self):
            self.name = provider_name
            self.audio_format = audio_format
            self.calls = []

        def synthesize(self, text):
            self.calls.append(text)
            return audio_data

    source_segments = [
        STTSegment(10, "Hallo", True),
        STTSegment(20, "Welt", True),
    ]
    tts = FakeTTS()
    audio_segments = []

    translations = run_streaming_cascade(
        "test.wav",
        stt_provider=FakeSTTProvider(source_segments),
        translation_provider=FakeTranslationProvider(),
        tts_provider=tts,
        on_audio=audio_segments.append,
    )

    assert tts.calls == ["EN: Hallo", "EN: Welt"]
    assert len(audio_segments) == 2

    assert [
        segment.source.source.segment_id
        for segment in audio_segments
    ] == [10, 20]

    for index, segment in enumerate(audio_segments):
        assert segment.source is translations[index]
        assert segment.source.source is source_segments[index]
        assert segment.audio == audio_data
        assert segment.audio_format == audio_format
        assert segment.provider == provider_name
        assert segment.synthesis_seconds >= 0
        assert (
            segment.completed_at_seconds
            >= segment.source.completed_at_seconds
        )


def test_tts_fehler_wird_weitergegeben():
    original_error = ValueError("TTS-Testfehler")

    class FailingTTS:
        name = "failing-tts"
        audio_format = "mp3"

        def synthesize(self, text):
            raise original_error

    with pytest.raises(RuntimeError) as caught:
        run_streaming_cascade(
            "test.wav",
            stt_provider=FakeSTTProvider(
                [STTSegment(1, "Hallo", True)]
            ),
            translation_provider=FakeTranslationProvider(),
            tts_provider=FailingTTS(),
            on_audio=lambda segment: None,
        )

    assert caught.value.__cause__ is original_error


def test_tts_blockiert_nicht_und_audio_entsteht_vor_streamende():
    second_translation_finished = Event()
    first_audio_received = Event()
    stream_finished = Event()

    audio_segments = []
    audio_before_stream_end = []

    class StreamingSTT:
        name = "streaming-stt"

        def stream(self, audio_path, on_segment, *, started_at):
            try:
                on_segment(STTSegment(1, "Hallo", True))
                on_segment(STTSegment(2, "Welt", True))

                if not first_audio_received.wait(timeout=5):
                    raise AssertionError(
                        "Keine Audioausgabe vor dem Ende des STT-Streams."
                    )
            finally:
                stream_finished.set()

    class Translator:
        name = "test-translator"

        def translate(self, text, *, source_lang, target_lang):
            if text == "Welt":
                second_translation_finished.set()

            return f"EN: {text}"

    class WaitingTTS:
        name = "waiting-tts"
        audio_format = "mp3"

        def synthesize(self, text):
            if text == "EN: Hallo":
                if not second_translation_finished.wait(timeout=5):
                    raise AssertionError(
                        "TTS blockiert die nächste Übersetzung."
                    )

            return text.encode("utf-8")

    def receive_audio(segment):
        audio_before_stream_end.append(
            not stream_finished.is_set()
        )
        audio_segments.append(segment)
        first_audio_received.set()

    translations = run_streaming_cascade(
        "test.wav",
        stt_provider=StreamingSTT(),
        translation_provider=Translator(),
        tts_provider=WaitingTTS(),
        on_audio=receive_audio,
    )

    assert stream_finished.is_set()
    assert second_translation_finished.is_set()
    assert audio_before_stream_end[0] is True

    assert [segment.source.segment_id for segment in translations] == [
        1,
        2,
    ]
    assert [
        segment.source.source.segment_id
        for segment in audio_segments
    ] == [1, 2]
    assert [segment.audio for segment in audio_segments] == [
        b"EN: Hallo",
        b"EN: Welt",
    ]