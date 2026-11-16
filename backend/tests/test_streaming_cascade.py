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