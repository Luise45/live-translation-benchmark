
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
from pathlib import Path
from urllib.parse import urlencode

import websocket


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


def transcribe_streaming(
    audio_path: str,
    output_path: str = "results/streaming/deepgram_stt.json",
) -> dict:
    """Streamt eine WAV-Datei an Deepgram und speichert das Ergebnis."""

    api_key = (os.getenv("DEEPGRAM_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY ist nicht gesetzt.")

    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(f"Audiodatei fehlt: {path}")

    # 1. Audioformat überprüfen
    with wave.open(str(path), "rb") as audio:
        channels = audio.getnchannels()
        sample_rate = audio.getframerate()
        sample_width = audio.getsampwidth()
        compression = audio.getcomptype()
        duration = audio.getnframes() / sample_rate

    if compression != "NONE" or sample_width != 2:
        raise ValueError("Unterstützt wird nur unkomprimiertes PCM16-WAV.")

    if channels not in (1, 2):
        raise ValueError("Die WAV-Datei muss Mono oder Stereo sein.")

    # Rohe PCM16-Daten werden als Mono übertragen.
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

    url = f"{DEEPGRAM_URL}?{parameters}"

    # 2. WebSocket-Verbindung herstellen
    print("Verbinde mit Deepgram ...")
    ws = websocket.create_connection(
        url,
        header=[f"Authorization: Token {api_key}"],
        timeout=10,
    )
    ws.settimeout(1.0)
    print("WebSocket verbunden.")

    stop = threading.Event()
    sender_done = threading.Event()
    sender_errors = []
    sender_finished_at = [0.0]

    interim_results = []
    final_results = []
    metadata = {}
    stats = {"chunks_sent": 0}

    started = time.perf_counter()

    # 3. Audiodaten in Echtzeit senden
    def send_audio():
        try:
            with wave.open(str(path), "rb") as audio:
                frames_per_chunk = max(
                    1, round(sample_rate * CHUNK_MS / 1000)
                )
                frames_sent = 0
                send_started = time.perf_counter()

                while not stop.is_set():
                    raw_chunk = audio.readframes(frames_per_chunk)

                    if not raw_chunk:
                        break

                    frame_count = len(raw_chunk) // (
                        channels * sample_width
                    )

                    chunk = to_mono(raw_chunk, channels)

                    # Übertragung im Tempo der Originalaufnahme
                    frames_sent += frame_count
                    deadline = send_started + frames_sent / sample_rate

                    delay = max(0, deadline - time.perf_counter())
                    if stop.wait(delay):
                        return

                    ws.send_binary(chunk)
                    stats["chunks_sent"] += 1

            if not stop.is_set():
                ws.send(json.dumps({"type": "CloseStream"}))

        except Exception as error:
            sender_errors.append(error)
            stop.set()
            ws.close()

        finally:
            sender_finished_at[0] = time.monotonic()
            sender_done.set()

    sender = threading.Thread(target=send_audio, daemon=True)
    sender.start()

    # 4. Transkriptionsergebnisse gleichzeitig empfangen
    try:
        while True:
            if sender_errors:
                raise RuntimeError(
                    "Audioübertragung fehlgeschlagen."
                ) from sender_errors[0]

            if (
                sender_done.is_set()
                and time.monotonic() - sender_finished_at[0]
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
                if not sender_done.is_set():
                    raise RuntimeError(
                        "WebSocket wurde während der "
                        "Audioübertragung geschlossen."
                    )
                break

            if not message:
                if not sender_done.is_set():
                    raise RuntimeError(
                        "WebSocket wurde vorzeitig geschlossen."
                    )
                break

            event = json.loads(message)
            event_type = event.get("type")

            if event_type == "Error":
                raise RuntimeError(
                    "Deepgram-API-Fehler: "
                    + str(event.get("description", event))
                )

            if event_type == "Metadata":
                metadata = event

            if event_type != "Results":
                continue

            alternatives = event.get("channel", {}).get(
                "alternatives", []
            )

            if not alternatives:
                continue

            text = alternatives[0].get("transcript", "").strip()

            if not text:
                continue

            received_at = round(
                time.perf_counter() - started, 3
            )

            if event.get("is_final", False):
                final_results.append({
                    "text": text,
                    "start": event.get("start"),
                    "duration": event.get("duration"),
                    "speech_final": event.get("speech_final", False),
                    "received_at_seconds": received_at,
                })
                print("[FINAL]", text)

            else:
                interim_results.append({
                    "text": text,
                    "received_at_seconds": received_at,
                })
                print("[INTERIM]", text)

    finally:
        stop.set()
        ws.close()
        sender.join(timeout=5)

    if sender_errors:
        raise RuntimeError(
            "Audioübertragung fehlgeschlagen."
        ) from sender_errors[0]

    if not final_results:
        raise RuntimeError(
            "Keine finalen Transkriptionsergebnisse erhalten."
        )

    # 5. Vollständiges Transkript zusammensetzen
    transcript = " ".join(
        item["text"] for item in final_results
    )

    result = {
        "input_audio": str(path),
        "provider": "deepgram",
        "model": "nova-3",
        "language": "de",
        "original_channels": channels,
        "stream_channels": 1,
        "sample_rate": sample_rate,
        "audio_duration_seconds": round(duration, 3),
        "chunk_ms": CHUNK_MS,
        "chunks_sent": stats["chunks_sent"],
        "interim_results": interim_results,
        "final_results": final_results,
        "transcript": transcript,
        "total_elapsed_seconds": round(
            time.perf_counter() - started, 3
        ),
        "request_id": metadata.get("request_id"),
    }

    # 6. Ergebnis als JSON speichern
    target = Path(output_path)
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

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Deepgram Nova-3 Streaming-STT"
    )
    parser.add_argument("audio", help="Pfad zur WAV-Testdatei")
    parser.add_argument(
        "--output",
        default="results/streaming/deepgram_stt.json",
        help="Pfad zur Ergebnisdatei",
    )

    args = parser.parse_args()

    try:
        transcribe_streaming(args.audio, args.output)
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
