"""
Deepgram Nova-3 Streaming Speech-to-Text.

Überträgt eine WAV-Datei in zeitlich getakteten Audio-Chunks
und empfängt vorläufige und finale Transkripte per WebSocket.
"""

import argparse
import json
import os
import struct
import threading
import time
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlencode

import websocket

from backend.app.core.models import STTSegment
from backend.app.core.models import SynthesizedSegment
from backend.app.benchmark.streaming_cascade import run_streaming_cascade
from backend.app.integrations.i_deepl import DeepLTranslationProvider
from backend.app.integrations.i_elevenlabs import ElevenLabsTTSProvider


DEEPGRAM_URL = "wss://api.deepgram.com/v1/listen"
CHUNK_MS = 100
RECEIVE_TIMEOUT = 20


def to_mono(pcm_data: bytes, channels: int) -> bytes:
    """Wandelt Stereo-PCM16 bei Bedarf in Mono-PCM16 um."""
    if channels == 1:
        return pcm_data

    samples = struct.unpack(
        f"<{len(pcm_data) // 2}h", pcm_data
    )
    mono = [
        (samples[i] + samples[i + 1]) // 2
        for i in range(0, len(samples), 2)
    ]
    return struct.pack(f"<{len(mono)}h", *mono)


@dataclass
class DeepgramStreamMetadata:
    """Technische Angaben einer Deepgram-Streaming-Sitzung."""

    original_channels: int
    sample_rate: int
    audio_duration_seconds: float
    chunks_sent: int = 0
    audio_finished_at_seconds: float | None = None
    request_id: str | None = None


class DeepgramStreamingProvider:
    """Überträgt WAV-Audio und liefert Deepgram-STT-Segmente."""

    name = "deepgram"

    def __init__(self) -> None:
        self.metadata: DeepgramStreamMetadata | None = None

    def stream(
        self,
        audio_path: str,
        on_segment: Callable[[STTSegment], None],
        *,
        started_at: float,
    ) -> None:
        self.metadata = None

        api_key = (os.getenv("DEEPGRAM_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("DEEPGRAM_API_KEY ist nicht gesetzt.")

        path = Path(audio_path)

        with wave.open(str(path), "rb") as audio:
            channels = audio.getnchannels()
            sample_rate = audio.getframerate()
            sample_width = audio.getsampwidth()
            compression = audio.getcomptype()
            duration = audio.getnframes() / sample_rate

        if compression != "NONE" or sample_width != 2:
            raise ValueError(
                "Unterstützt wird nur unkomprimiertes PCM16-WAV."
            )

        if channels not in (1, 2):
            raise ValueError(
                "Die WAV-Datei muss Mono oder Stereo sein."
            )

        metadata = DeepgramStreamMetadata(
            original_channels=channels,
            sample_rate=sample_rate,
            audio_duration_seconds=duration,
        )
        self.metadata = metadata

        parameters = urlencode({
            "model": "nova-3",
            "language": "de",
            "encoding": "linear16",
            "sample_rate": sample_rate,
            "channels": 1,
            "interim_results": "true",
            "endpointing": 300,
            "smart_format": "true",
        })

        ws = websocket.create_connection(
            f"{DEEPGRAM_URL}?{parameters}",
            header=[f"Authorization: Token {api_key}"],
            timeout=10,
        )

        stop = threading.Event()
        sender_done = threading.Event()
        sender_errors: list[Exception] = []
        sender_finished_at = 0.0

        def send_audio() -> None:
            nonlocal sender_finished_at

            try:
                with wave.open(str(path), "rb") as audio:
                    frames_per_chunk = max(
                        1,
                        round(sample_rate * CHUNK_MS / 1000),
                    )
                    frames_sent = 0
                    send_started = time.perf_counter()

                    while not stop.is_set():
                        raw_chunk = audio.readframes(frames_per_chunk)

                        if not raw_chunk:
                            break

                        frames_sent += len(raw_chunk) // (
                            channels * sample_width
                        )
                        deadline = (
                            send_started + frames_sent / sample_rate
                        )
                        delay = max(
                            0.0,
                            deadline - time.perf_counter(),
                        )

                        if stop.wait(delay):
                            return

                        ws.send_binary(to_mono(raw_chunk, channels))
                        metadata.chunks_sent += 1

                if not stop.is_set():
                    metadata.audio_finished_at_seconds = (
                        time.perf_counter() - started_at
                    )
                    ws.send(json.dumps({"type": "CloseStream"}))

            except Exception as error:
                sender_errors.append(error)
                stop.set()

            finally:
                sender_finished_at = time.monotonic()
                sender_done.set()

        sender = threading.Thread(
            target=send_audio,
            name="deepgram-audio-sender",
        )

        try:
            ws.settimeout(1.0)
            sender.start()

            next_segment_id = 1

            while True:
                if sender_errors:
                    raise RuntimeError(
                        "Audioübertragung fehlgeschlagen."
                    ) from sender_errors[0]

                if (
                    sender_done.is_set()
                    and time.monotonic() - sender_finished_at
                    > RECEIVE_TIMEOUT
                ):
                    raise TimeoutError(
                        "Deepgram hat die Streaming-Sitzung "
                        "nicht rechtzeitig abgeschlossen."
                    )

                try:
                    message = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except websocket.WebSocketConnectionClosedException:
                    message = ""

                if not message:
                    # CloseStream kann bereits beantwortet werden,
                    # bevor der Sender seinen Abschluss signalisiert.
                    if not sender_done.wait(timeout=1.0):
                        raise RuntimeError(
                            "WebSocket wurde während der "
                            "Audioübertragung geschlossen."
                        )

                    if sender_errors:
                        raise RuntimeError(
                            "Audioübertragung fehlgeschlagen."
                        ) from sender_errors[0]

                    break

                event = json.loads(message)

                if event.get("type") == "Metadata":
                    metadata.request_id = event.get("request_id")
                    continue

                if event.get("type") == "Error":
                    raise RuntimeError(
                        "Deepgram meldet einen Fehler: "
                        + str(event.get("description", "Unbekannt"))
                    )

                if event.get("type") != "Results":
                    continue

                alternatives = event.get("channel", {}).get(
                    "alternatives", []
                )
                if not alternatives:
                    continue

                text = alternatives[0].get("transcript", "").strip()
                if not text:
                    continue

                is_final = bool(event.get("is_final", False))

                segment = STTSegment(
                    segment_id=next_segment_id,
                    text=text,
                    is_final=is_final,
                    start_seconds=event.get("start"),
                    duration_seconds=event.get("duration"),
                    received_at_seconds=(
                        time.perf_counter() - started_at
                    ),
                    speech_final=bool(
                        event.get("speech_final", False)
                    ),
                )

                on_segment(segment)

                if is_final:
                    next_segment_id += 1

        finally:
            stop.set()

            try:
                ws.close()
            finally:
                if sender.ident is not None:
                    sender.join()


def transcribe_streaming(
    audio_path: str,
    output_path: str = "results/streaming/deepgram_stt.json",
    target_lang: str = "EN-US",
    enable_tts: bool = False,
) -> dict:
    """Startet die Streaming-Kaskade und speichert Text und optional Audio."""

    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(f"Audiodatei fehlt: {path}")

    # Fehlende TTS-Konfiguration vor dem Start der Audioübertragung melden.
    if enable_tts:
        for variable in ("ELEVEN_API_KEY", "VOICE_ID"):
            if not (os.getenv(variable) or "").strip():
                raise RuntimeError(
                    f"Umgebungsvariable fehlt: {variable}"
                )

    stt_provider = DeepgramStreamingProvider()
    translation_provider = DeepLTranslationProvider()
    tts_provider = ElevenLabsTTSProvider() if enable_tts else None

    target = Path(output_path)

    # Eigener Audioordner pro Durchlauf verhindert das Überschreiben
    # von Segmentdateien vorheriger Durchläufe.
    audio_dir = (
        target.parent / f"{target.stem}_audio_{uuid4().hex}"
        if enable_tts
        else None
    )

    received_segments: list[STTSegment] = []
    audio_results: list[dict] = []
    started_at = time.perf_counter()

    def save_audio(segment: SynthesizedSegment) -> None:
        """Speichert jedes fertige Segment direkt im TTS-Worker."""

        if audio_dir is None:
            raise RuntimeError("Kein Audio-Ausgabeordner konfiguriert.")

        available_at = time.perf_counter() - started_at
        sequence = len(audio_results) + 1
        segment_id = segment.source.source.segment_id

        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_file = audio_dir / f"segment_{sequence:06d}.mp3"
        audio_file.write_bytes(segment.audio)

        audio_results.append({
            "sequence": sequence,
            "segment_id": segment_id,
            "translated_text": segment.source.text,
            "provider": segment.provider,
            "audio_format": segment.audio_format,
            "audio_path": str(audio_file),
            "synthesis_seconds": round(
                segment.synthesis_seconds, 3
            ),
            "completed_at_seconds": round(
                segment.completed_at_seconds, 3
            ),
            "available_at_seconds": round(available_at, 3),
            "saved_at_seconds": round(
                time.perf_counter() - started_at, 3
            ),
        })

        print(f"[AUDIO] Segment {segment_id}: {audio_file}")

    translated_segments = run_streaming_cascade(
        str(path),
        stt_provider=stt_provider,
        translation_provider=translation_provider,
        source_lang="DE",
        target_lang=target_lang,
        tts_provider=tts_provider,
        on_audio=save_audio if enable_tts else None,
        on_segment=received_segments.append,
        started_at=started_at,
    )

    final_segments = [
        segment
        for segment in received_segments
        if segment.is_final
    ]

    if not final_segments:
        raise RuntimeError(
            "Keine finalen Transkriptionsergebnisse erhalten."
        )

    metadata = stt_provider.metadata
    if metadata is None:
        raise RuntimeError(
            "Deepgram hat keine Sitzungsmetadaten bereitgestellt."
        )

    interim_results = [
        {
            "text": segment.text,
            "received_at_seconds": round(
                segment.received_at_seconds, 3
            ),
        }
        for segment in received_segments
        if not segment.is_final
    ]

    final_results = [
        {
            "segment_id": segment.segment_id,
            "text": segment.text,
            "start": segment.start_seconds,
            "duration": segment.duration_seconds,
            "speech_final": segment.speech_final,
            "received_at_seconds": round(
                segment.received_at_seconds, 3
            ),
        }
        for segment in final_segments
    ]

    translation_results = [
        {
            "segment_id": segment.source.segment_id,
            "original_text": segment.source.text,
            "translated_text": segment.text,
            "translation_seconds": round(
                segment.translation_seconds, 3
            ),
            "completed_at_seconds": round(
                segment.completed_at_seconds, 3
            ),
        }
        for segment in translated_segments
    ]

    transcript = " ".join(
        segment.text for segment in final_segments
    )

    audio_finished_at = metadata.audio_finished_at_seconds

    result = {
        "input_audio": str(path),
        "provider": stt_provider.name,
        "model": "nova-3",
        "language": "de",
        "original_channels": metadata.original_channels,
        "stream_channels": 1,
        "sample_rate": metadata.sample_rate,
        "audio_duration_seconds": round(
            metadata.audio_duration_seconds, 3
        ),
        "audio_finished_at_seconds": (
            round(audio_finished_at, 3)
            if audio_finished_at is not None
            else None
        ),
        "chunk_ms": CHUNK_MS,
        "chunks_sent": metadata.chunks_sent,
        "interim_results": interim_results,
        "final_results": final_results,
        "transcript": transcript,
        "translation_provider": translation_provider.name,
        "target_language": target_lang,
        "translation_results": translation_results,
        "translated_segments": len(translation_results),
        "total_elapsed_seconds": round(
            time.perf_counter() - started_at, 3
        ),
        "request_id": metadata.request_id,
    }

    if enable_tts:
        result.update({
            "tts_provider": tts_provider.name,
            "audio_results": audio_results,
            "synthesized_segments": len(audio_results),
            "time_to_first_audio_seconds": (
                audio_results[0]["available_at_seconds"]
                if audio_results
                else None
            ),
        })

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== STREAMING-ERGEBNIS ===")
    print("Transkript:", transcript)
    print("Audio-Dauer:", result["audio_duration_seconds"], "s")
    print("Gesamtdauer:", result["total_elapsed_seconds"], "s")
    print("JSON:", target)

    if enable_tts:
        print("Erzeugte Audiosegmente:", len(audio_results))

    return result

def main():
    parser = argparse.ArgumentParser(
        description="Streaming-Kaskade mit optionaler ElevenLabs-Ausgabe"
    )
    parser.add_argument(
        "audio",
        help="Pfad zur WAV-Testdatei",
    )
    parser.add_argument(
        "--output",
        default="results/streaming/deepgram_stt.json",
        help="Pfad zur Ergebnisdatei",
    )
    parser.add_argument(
        "--target-lang",
        default="EN-US",
        help="DeepL-Zielsprache, z. B. EN-US, FR oder ES",
    )
    parser.add_argument(
        "--tts",
        action="store_true",
        help="Übersetzte Segmente mit ElevenLabs als MP3 ausgeben",
    )

    args = parser.parse_args()

    try:
        transcribe_streaming(
            args.audio,
            args.output,
            target_lang=args.target_lang,
            enable_tts=args.tts,
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        TimeoutError,
        wave.Error,
        websocket.WebSocketException,
    ) as error:
        parser.exit(1, f"Streaming fehlgeschlagen: {error}\n")

if __name__ == "__main__":
    main()