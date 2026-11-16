"""Providerunabhängige Steuerung von Streaming-STT und Übersetzung."""

import time
from queue import Queue
from threading import Thread

from backend.app.core.interfaces import (
    StreamingSTTProvider,
    TranslationProvider,
)
from backend.app.core.models import STTSegment, TranslatedSegment


def run_streaming_cascade(
    audio_path: str,
    *,
    stt_provider: StreamingSTTProvider,
    translation_provider: TranslationProvider,
    source_lang: str = "DE",
    target_lang: str = "EN-US",
) -> list[TranslatedSegment]:
    """Übersetzt finale STT-Segmente während der Transkription.

    Ein einzelner Worker verarbeitet die Segmente in Empfangsreihenfolge.
    Die Funktion wartet auf alle Übersetzungen und gibt deren Ergebnisse
    zurück. Fehler der Provider werden an den Aufrufer weitergegeben.
    """

    started_at = time.perf_counter()
    segments: Queue[STTSegment | None] = Queue()
    results: list[TranslatedSegment] = []
    translation_errors: list[Exception] = []

    def receive_segment(segment: STTSegment) -> None:
        """Übergibt nur finale, nicht leere Segmente an den Worker."""
        if segment.is_final and segment.text.strip():
            segments.put(segment)

    def translate_segments() -> None:
        while True:
            segment = segments.get()

            try:
                if segment is None:
                    return

                # Nach einem Fehler keine weiteren Provider-Aufrufe starten.
                # Die Warteschlange wird bis zum Abschluss weiter geleert.
                if translation_errors:
                    continue

                translation_started = time.perf_counter()

                translated_text = translation_provider.translate(
                    segment.text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                )

                completed_at = time.perf_counter()

                if not translated_text.strip():
                    raise ValueError(
                        "Leere Übersetzung für Segment "
                        f"{segment.segment_id}."
                    )

                results.append(
                    TranslatedSegment(
                        source=segment,
                        text=translated_text,
                        provider=translation_provider.name,
                        translation_seconds=(
                            completed_at - translation_started
                        ),
                        completed_at_seconds=completed_at - started_at,
                    )
                )

            except Exception as error:
                translation_errors.append(error)

            finally:
                segments.task_done()

    translator = Thread(
        target=translate_segments,
        name="streaming-translation",
    )
    translator.start()

    try:
        stt_provider.stream(
            audio_path,
            on_segment=receive_segment,
            started_at=started_at,
        )
    finally:
        # Das Endsignal folgt allen bereits empfangenen Segmenten.
        # Auch bei einem STT-Fehler wird der Worker sauber beendet.
        segments.put(None)
        translator.join()

    if translation_errors:
        raise RuntimeError(
            "Die Übersetzung in der Streaming-Kaskade ist fehlgeschlagen."
        ) from translation_errors[0]

    return results