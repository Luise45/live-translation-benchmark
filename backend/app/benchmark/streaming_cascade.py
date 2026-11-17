"""Providerunabhängige Streaming-Kaskade für STT, Übersetzung und TTS."""

import time
from collections.abc import Callable
from queue import Queue
from threading import Event, Thread

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
    """Verarbeitet STT, Übersetzung und optional TTS unabhängig.

    Finale STT-Segmente werden in Empfangsreihenfolge übersetzt.
    Ein separater TTS-Worker verarbeitet die Übersetzungen ebenfalls
    nacheinander. TTS blockiert dadurch nicht den Übersetzungs-Worker.

    on_segment läuft im STT-Empfangspfad.
    on_audio läuft im TTS-Worker.
    Beide Callbacks sollten nur kurz arbeiten.

    started_at ist ein gemeinsamer time.perf_counter()-Startwert.
    Die Funktion wartet auf beide Worker und gibt die Übersetzungen
    zurück. Bereits ausgegebene Audiosegmente bleiben bei späteren
    Fehlern bestehen.

    Provider müssen ihre Netzwerkaufrufe durch Zeitlimits begrenzen.
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

    stt_segments: Queue[STTSegment | None] = Queue()
    translated_segments: Queue[TranslatedSegment | None] = Queue()
    processing_errors: Queue[Exception] = Queue()
    failed = Event()

    results: list[TranslatedSegment] = []

    def record_error(error: Exception) -> None:
        processing_errors.put(error)
        failed.set()

    def receive_segment(segment: STTSegment) -> None:
        if on_segment is not None:
            on_segment(segment)

        if (
            segment.is_final
            and segment.text.strip()
            and not failed.is_set()
        ):
            stt_segments.put(segment)

    def translate_segments() -> None:
        try:
            while True:
                segment = stt_segments.get()

                if segment is None:
                    return

                if failed.is_set():
                    continue

                try:
                    translation_started = time.perf_counter()

                    text = translation_provider.translate(
                        segment.text,
                        source_lang=source_lang,
                        target_lang=target_lang,
                    )

                    translation_finished = time.perf_counter()

                    if not text.strip():
                        raise ValueError(
                            "Leere Übersetzung für Segment "
                            f"{segment.segment_id}."
                        )

                    translated = TranslatedSegment(
                        source=segment,
                        text=text,
                        provider=translation_provider.name,
                        translation_seconds=(
                            translation_finished - translation_started
                        ),
                        completed_at_seconds=(
                            translation_finished - cascade_started_at
                        ),
                    )

                    results.append(translated)

                    if tts_provider is not None and not failed.is_set():
                        translated_segments.put(translated)

                except Exception as error:
                    record_error(error)

        finally:
            # Erst nach der letzten Übersetzung endet die TTS-Eingabe.
            if tts_provider is not None:
                translated_segments.put(None)

    def synthesize_segments() -> None:
        if tts_provider is None or on_audio is None:
            return

        while True:
            segment = translated_segments.get()

            if segment is None:
                return

            if failed.is_set():
                continue

            try:
                synthesis_started = time.perf_counter()

                audio = tts_provider.synthesize(segment.text)

                synthesis_finished = time.perf_counter()

                if not audio:
                    raise ValueError(
                        "Leere TTS-Ausgabe für Segment "
                        f"{segment.source.segment_id}."
                    )

                on_audio(
                    SynthesizedSegment(
                        source=segment,
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
                record_error(error)

    translation_worker = Thread(
        target=translate_segments,
        name="streaming-translation",
    )

    tts_worker = (
        Thread(
            target=synthesize_segments,
            name="streaming-tts",
        )
        if tts_provider is not None
        else None
    )

    if tts_worker is not None:
        tts_worker.start()

    try:
        translation_worker.start()
    except Exception:
        # Auch bei einem Startfehler keinen wartenden TTS-Thread hinterlassen.
        if tts_worker is not None:
            translated_segments.put(None)
            tts_worker.join()
        raise

    try:
        stt_provider.stream(
            audio_path,
            on_segment=receive_segment,
            started_at=cascade_started_at,
        )
    finally:
        stt_segments.put(None)
        translation_worker.join()

        if tts_worker is not None:
            tts_worker.join()

    if not processing_errors.empty():
        raise RuntimeError(
            "Die Verarbeitung in der Streaming-Kaskade ist fehlgeschlagen."
        ) from processing_errors.get()

    return results