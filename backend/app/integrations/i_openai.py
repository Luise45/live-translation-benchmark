
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

# - die Funktion für die Übersetzung -
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

   