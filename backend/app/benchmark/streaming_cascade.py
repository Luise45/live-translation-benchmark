"""Providerunabhängige Streaming-Kaskade für STT, Übersetzung und TTS."""

import time
from collections.abc import Callable
from queue import Queue
from threading import Thread

from backend.app.core.interfaces import (
    StreamingSTTProvider,
    TranslationProvider,
    TTSProvider,
)
from backend.app.core.models import (
    STTSegment,
    SynthesizedSegment,
    TranslatedSegment,
)


def run_streaming_cascade(
    audio_path: str,
    *,
    stt_provider: StreamingSTTProvider,
    translation_provider: TranslationProvider,
    source_lang: str = "DE",
    target_lang: str = "EN-US",
    tts_provider: TTSProvider | None = None,
    on_audio: Callable[[SynthesizedSegment], None] | None = None,
    on_segment: Callable[[STTSegment], None] | None = None,
    started_at: float | None = None,
) -> list[TranslatedSegment]:
    """Verarbeitet finale STT-Segmente in Empfangsreihenfolge.

    Ein Worker übersetzt die Segmente und erzeugt optional Audio.
    Der STT-Empfang läuft unabhängig davon weiter.

    on_segment erhält alle STT-Segmente im Empfangspfad.
    on_audio erhält erzeugte Audiosegmente im Worker.
    Beide Callbacks sollten nur kurz arbeiten.

    Bei aktiviertem TTS ist on_audio erforderlich, damit die Audiodaten
    an den Aufrufer weitergegeben werden.

    started_at ist der gemeinsame time.perf_counter()-Startwert.
    Ohne Vorgabe wird beim Funktionsaufruf eine neue Zeitbasis erstellt.

    Die Funktion wartet auf den Worker und gibt die Übersetzungen zurück.
    Fehler werden an den Aufrufer weitergegeben. Bereits an Callbacks
    übergebene Ergebnisse können bei einem späteren Fehler vorliegen.
    """

    if tts_provider is not None and on_audio is None:
        raise ValueError(
            "Bei aktiviertem TTS muss on_audio angegeben werden."
        )

    if tts_provider is None and on_audio is not None:
        raise ValueError(
            "Für on_audio muss ein TTS-Provider angegeben werden."
        )

    cascade_started_at = (
        time.perf_counter() if started_at is None else started_at
    )

    segments: Queue[STTSegment | None] = Queue()
    results: list[TranslatedSegment] = []
    processing_errors: list[Exception] = []

    def receive_segment(segment: STTSegment) -> None:
        if on_segment is not None:
            on_segment(segment)

        if segment.is_final and segment.text.strip():
            segments.put(segment)

    def process_segments() -> None:
        while True:
            segment = segments.get()

            try:
                if segment is None:
                    return

                # Nach einem Fehler keine weiteren Provider-Aufrufe.
                # Die Warteschlange wird bis zum Endsignal geleert.
                if processing_errors:
                    continue

                translation_started = time.perf_counter()

                translated_text = translation_provider.translate(
                    segment.text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                )

                translation_finished = time.perf_counter()

                if not translated_text.strip():
                    raise ValueError(
                        "Leere Übersetzung für Segment "
                        f"{segment.segment_id}."
                    )

                translated_segment = TranslatedSegment(
                    source=segment,
                    text=translated_text,
                    provider=translation_provider.name,
                    translation_seconds=(
                        translation_finished - translation_started
                    ),
                    completed_at_seconds=(
                        translation_finished - cascade_started_at
                    ),
                )
                results.append(translated_segment)

                if tts_provider is not None and on_audio is not None:
                    synthesis_started = time.perf_counter()

                    audio = tts_provider.synthesize(translated_text)

                    synthesis_finished = time.perf_counter()

                    if not audio:
                        raise ValueError(
                            "Leere TTS-Ausgabe für Segment "
                            f"{segment.segment_id}."
                        )

                    on_audio(
                        SynthesizedSegment(
                            source=translated_segment,
                            audio=audio,
                            audio_format=tts_provider.audio_format,
                            provider=tts_provider.name,
                            synthesis_seconds=(
                                synthesis_finished - synthesis_started
                            ),
                            completed_at_seconds=(
                                synthesis_finished - cascade_started_at
                            ),
                        )
                    )

            except Exception as error:
                processing_errors.append(error)

            finally:
                segments.task_done()

    worker = Thread(
        target=process_segments,
        name="streaming-cascade-worker",
    )
    worker.start()

    try:
        stt_provider.stream(
            audio_path,
            on_segment=receive_segment,
            started_at=cascade_started_at,
        )
    finally:
        # Das Endsignal folgt allen bereits empfangenen Segmenten.
        # Auch bei einem STT-Fehler wird auf den Worker gewartet.
        segments.put(None)
        worker.join()

    if processing_errors:
        raise RuntimeError(
            "Die Verarbeitung in der Streaming-Kaskade ist fehlgeschlagen."
        ) from processing_errors[0]

    return results