
'''
Integration für OpenAI Realtime API für Übersetzungen

braucht: pip install websocket-client numpy python-dotenv

Wav --> zu --> Wav Übersetzung
Quellen und Hilfe für den Code:

https://developers.openai.com/api/docs/guides/voice-websockets?api=realtime&connection-example=python
https://developers.openai.com/api/docs/guides/realtime-conversations#handling-audio-with-websockets
https://github.com/KhalidAbdelaty/gpt-realtime-api/blob/main/test2_translation.py
https://developers.openai.com/api/docs/guides/realtime-translation#close-a-websocket-session

'''


import argparse
import base64
import json
import os
import threading
import time
from tracemalloc import start
import wave
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

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

def elapsed_ms(end, start):
    if end is None or start is None:
        return None
    return round((end - start) * 1000, 2)

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
        input_duration = audio.getnframes() / SAMPLE_RATE
    # API-Schlüssel gelesen. 
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Set OPENAI_API_KEY in .env")
    
    timing = {"input_start": None, "input_end": None,
              "first_output_audio": None,
              "last_output_audio": None
    }

    # Vorbereitungen für das spätere Senden und Empfangen. Die Aufgaben sind: Stoppsignal für threads, Fehler sammenl, Platzhalter für den kommenden Sender-Thread.
    stop = threading.Event()
    sender_errors, transcript, source_transcript, audio_chunks = [], [], [], []
    sender = None

      # Gesammelt werden: übersetzter Text, erkannter Originaltext, übersetztes Audio.
    transcript = []
    source_transcript = []
    audio_chunks = []

    #Verbindung wird geöffnet
    ws = websocket.create_connection(
        URL, header=[f"Authorization: Bearer {api_key}"], timeout=60,)
   
    
# - Funktion organisiert den Vorgang des Sendens. Audio_send sendet dan die Datei.in Stücken an den Server, während der Hauptthread gleichzeitig Antworten empfängt.
    def send_audio():
        try:
            with wave.open(str(audio_path), "rb") as audio:
                   # Startzeit der Eingabe merken, Basis für die Latenzmessung
                 timing["input_start"] = time.perf_counter()
                   # Zeitpunkt, zu dem das nächste Stück gesendet werden soll
                 deadline = time.perf_counter()
                 while not stop.is_set():
                    chunk = audio.readframes(CHUNK_FRAMES)
                     # Leeres Stück = Datei zu Ende
                    if not chunk:
                        break

                    ws.send(json.dumps({
                       "type": "session.input_audio_buffer.append",
                       "audio": base64.b64encode(chunk).decode("ascii"),
             }))
                     # Dauer des Stücks berechnen (2 Bytes pro Messwert)
                    deadline += len(chunk) / (SAMPLE_RATE * 2)
                      # Warten, bis das nächste Stück dran ist. So wird in Echtzeit gesendet
                    if stop.wait(max(0, deadline - time.perf_counter())):
                        return
            # Ende der Eingabe merken, Basis für den completion_lag
            if not stop.is_set():
                timing["input_end"] = time.perf_counter()
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
        # sender thread starten. Gleichzeitig seenden und empfangen.
        sender = threading.Thread(target=send_audio, daemon=True)
       
        sender.start()
        while True:
            event = receive(ws)
            received_at = time.perf_counter()
            if event["type"] == "session.output_audio.delta":
                # das Format muss stimmen 
                if (event.get("sample_rate", SAMPLE_RATE) != SAMPLE_RATE
                        or event.get("channels", 1) != 1
                        or event.get("format", "pcm16") != "pcm16"):
                    raise RuntimeError("Received unexpected audio format")
                data = base64.b64decode(event["delta"], validate=True)
                if data:
                 audio_chunks.append(data)
                 # Latenz messen, wann das erste Audio ankommt und wann das letzte Audio ankommt
                if timing["first_output_audio"] is None:
                 timing["first_output_audio"] = received_at
                 timing["last_output_audio"] = received_at
               
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
   
   # Latenz berechnen und zurückgeben.
    latency = {
        "first_audio_latency_ms": elapsed_ms(
            timing["first_output_audio"], timing["input_start"]
        ),
        "completion_lag_ms": elapsed_ms(
            timing["last_output_audio"], timing["input_end"]
        ),
        "input_duration_seconds": round(input_duration, 3),
    }
        # Gibt den Übersetzten Text und den Originaltext zurück.
    return "".join(source_transcript), "".join(transcript), latency

'''
sucht nach der env Datei, liest die Eingabedatei, die Ausgabedatei und die Zielsprache ein.
ruft die Funktion translate auf und speichert die Transkripte in einer JSON Datei.

'''
# Übersetzt alle Gesprächsbeiträge (Turns) nacheinander.
def translate_turns(turns, out_dir: Path):
      # ordner anlegen, falls er noch nicht existiert
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []


    for number, (speaker, audio_path, target_language) in enumerate(turns, 1):
        output_path = out_dir / f"{number:03d}_{speaker}_{target_language}.wav"

        print(f"Translating turn {number}: {speaker}")
   # Genau ein Aufruf pro Turn
        source, translation, latency = translate(
            audio_path,
            output_path,
            target_language,
        )
          
        results.append({
            "turn": number,
            "speaker": speaker,
            "input_file": str(audio_path),
            "output_file": str(output_path),
            "target_language": target_language,
            "source_transcript": source,
            "translated_transcript": translation,
            "metrics": {
              "latency": latency,
              "translation_accuracy": None,
              "critical_information": None,
              "terminology": None,
},
        })
      
        # nach jedem turn speichern   
        (out_dir / "conversation.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return results
    
def parse_args():
    
    parser = argparse.ArgumentParser(
        description="Translate WAV turns (24 kHz, mono, PCM16) with OpenAI realtime translation."
    )
    # --turn für jeden Gesprächsbeitrag, --out für den Ausgabeordner
    parser.add_argument(
        "--turn",
        nargs=3,
        action="append",
        required=True,
        metavar=("SPEAKER", "AUDIO_FILE", "TARGET_LANG"),
        help="One conversation turn. Repeat for each turn. TARGET_LANG is the "
             "language to translate INTO (e.g. en, de).",
    )
    parser.add_argument("--out", type=Path, default=Path("out"),
                        help="Output directory (default: .../out)")
    return parser.parse_args()


def main():
    for directory in (Path(__file__).resolve().parent, *Path(__file__).resolve().parents):
        if (directory / ".env").is_file():
            load_dotenv(directory / ".env")
            break

    args = parse_args()

    turns = []
    for speaker, audio_file, target_language in args.turn:
        audio_path = Path(audio_file)
        if not audio_path.is_file():
            raise SystemExit(f"Audio file not found: {audio_path}")
        turns.append((speaker, audio_path, target_language))

    results = translate_turns(turns, args.out)
# Console Ausgaben 
    for turn in results:
        print(f"\n{turn['turn']}. {turn['speaker']}")
        print(f"Original: {turn['source_transcript']}")
        print(f"Translation: {turn['translated_transcript']}")
        print(f"Latency: {turn['metrics']['latency']}")

# wird beim Aufruf des Skripts/ Datei ausgeführt.
if __name__ == "__main__":
    main()

