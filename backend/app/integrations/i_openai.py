
'''
Integration für OpenAI Realtime API für Übersetzungen

braucht: pip install websocket-client numpy python-dotenv

Wav --> zu --> Wav Übersetzung
'''


import argparse
import base64
import json
import os
import threading
import time
import wave
from pathlib import Path

import websocket
from dotenv import load_dotenv
import numpy as np


# Verbindung herstellen und Audio zerlegen. Audiomesswerte pro Sekunde unf Messwerte pro Nachricht. Wss für WebSocket Secure Verbindung. 
URL = "wss://api.openai.com/v1/realtime/translations?model=gpt-realtime-translate"
SAMPLE_RATE = 24000
CHUNK_FRAMES = 4800  

# receive wartet auf die Nachricht vom Server. Event ist was gerade passiert z.B session created oder error mit exception. 
def receive(ws):
    message = ws.recv()
    if not message:
        raise RuntimeError("Connection ended before session.closed")
    event = json.loads(message)
    if event.get("type") == "error":
        error = event.get("error", {})
        raise RuntimeError(f"OpenAI: {error.get('message', error)}")
    return event

# liest so lange Nachrichten vom Server bis das gewünschte Event eintrifft. Pass: keine weitere Aktion, nur warten.
def wait_for(ws, event_type):
    while receive(ws).get("type") != event_type:
        pass

# - Funktion für Audio checken und Verbindung herstellen  -
'''
Die Funktion bekommt 3 Angaben, einmal die Eingabedatei, die Ausgabedatei und die Zeilsprache. 
Testet ob output und input Datein gleich sind -> error.
'''
def translate(audio_path: Path, output_path: Path, target_language: str = "en"):
    if audio_path.resolve() == output_path.resolve():
        raise ValueError("Input and output paths must be different")

    # Audioformat wird kontrolliert, es muss mono, 16Bit (zwei Bytes pro Messwert), 24 kHz und nicht zip sein.
    with wave.open(str(audio_path), "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(),
                audio.getcomptype()) != (1, 2, SAMPLE_RATE, "NONE"):
            raise ValueError("Input must be a 24 kHz, mono, PCM16 WAV file")
        if audio.getnframes() == 0:
            raise ValueError("Input recording is empty")
    # API-Schlüssel gelesen. 
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Set OPENAI_API_KEY in .env")

    stop = threading.Event()
    sender_errors = []
    sender = None
    # übersetzter text, erkannter Orginaltext und übersetzt Audiodaten werden gesammelt. 
    transcript = []
    source_transcript = []
    audio_chunks = []
    #Verbindung wird geöffnet
    ws = websocket.create_connection(
        URL, header=[f"Authorization: Bearer {api_key}"], timeout=60,
    )
# - Funktion sendet Datei- 
    def send_audio():
        try:
            with wave.open(str(audio_path), "rb") as audio:
                deadline = time.perf_counter()
                while not stop.is_set():
                # Wav wird in Stücken gesendet. Jedes Stück ist in einer JSON Nachricht verpackt. 
                    chunk = audio.readframes(CHUNK_FRAMES)
                    if not chunk:
                        break
                    ws.send(json.dumps({
                        "type": "session.input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode("ascii"),
                    }))
                    # berechnet Dauer des Audiostücks
                    deadline += len(chunk) / (SAMPLE_RATE * 2)
                    if stop.wait(max(0, deadline - time.perf_counter())):
                        return
            if not stop.is_set():
                ws.send(json.dumps({"type": "session.close"}))
        except Exception as exc:
            sender_errors.append(exc)
            ws.abort()  

    try:
        wait_for(ws, "session.created")
        ws.send(json.dumps({
            "type": "session.update",
            "session": {"audio": {
                "input": {"transcription": {"model": "gpt-realtime-whisper"}},
                "output": {"language": target_language},
            }},
        }))
        wait_for(ws, "session.updated")

        sender = threading.Thread(target=send_audio, daemon=True)
        sender.start()
        while True:
            event = receive(ws)
            if event["type"] == "session.output_audio.delta":
                if (event.get("sample_rate", SAMPLE_RATE) != SAMPLE_RATE
                        or event.get("channels", 1) != 1
                        or event.get("format", "pcm16") != "pcm16"):
                    raise RuntimeError("Received unexpected audio format")
                audio_chunks.append(base64.b64decode(event["delta"], validate=True))
            elif event["type"] == "session.input_transcript.delta":
                source_transcript.append(event["delta"])
            elif event["type"] == "session.output_transcript.delta":
                transcript.append(event["delta"])
            elif event["type"] == "session.closed":
                break
    except Exception:
        if sender_errors:
            raise RuntimeError("Audio sending failed") from sender_errors[0]
        raise
    # sagt Stop und schlißt die Verbindung. Wartet auf den Sender-Thread, bis er fertig ist
    finally:
        stop.set()
        ws.close()
        if sender is not None:
            sender.join(timeout=5)

    if sender_errors:
        raise RuntimeError("Audio sending failed") from sender_errors[0]
    if not audio_chunks:
        raise RuntimeError("Session finished without translated audio")

    with wave.open(str(output_path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        audio.writeframes(b"".join(audio_chunks))
        # Gibt den Übersetzten Text und den Originaltext zurück.
    return "".join(source_transcript), "".join(transcript)

'''
sucht nach der env Datei, liest die Eingabedatei, die Ausgabedatei und die Zielsprache ein.
ruft die Funktion translate auf und speichert die Transkripte in einer JSON Datei.
Zeigt Texte und Speicherorte an.
'''

def main():
    # Search from the script folder upwards, including backend/.env.
    for directory in (Path(__file__).resolve().parent, *Path(__file__).resolve().parents):
        if (directory / ".env").is_file():
            load_dotenv(directory / ".env")
            break
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="24 kHz mono PCM16 WAV recording")
    parser.add_argument("--target", default="en", help="Target language code (default: en)")
    parser.add_argument("--output", type=Path, default=Path("translated.wav"))
    args = parser.parse_args()
    try:
        # ruft Funktion translate auf
        source, text = translate(args.input, args.output, args.target)
        # schreibt die Ergebnisse in die json Datei ein und macht print der Ergebnisse auf die Konsole. 
        transcript_path = args.output.with_suffix(".transcripts.json")
        transcript_path.write_text(json.dumps({
            "input_file": str(args.input),
            "target_language": args.target,
            "source_transcript": source,
            "translated_transcript": text,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, RuntimeError, wave.Error, websocket.WebSocketException) as exc:
        parser.exit(1, f"Translation failed: {exc}\n")
    print(f"Source: {source}")
    print(f"Translation: {text}")
    print(f"Audio saved to: {args.output.resolve()}")
    print(f"Transcripts saved to: {transcript_path.resolve()}")

# wird beim Aufruf des Skripts/ Datei ausgeführt.
if __name__ == "__main__":
    main()

