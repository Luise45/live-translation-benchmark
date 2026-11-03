
"""
Integration für OpenAI Realtime API für Übersetzungen

braucht: pip install websocket-client numpy python-dotenv

Wav --> zu --> Wav Übersetzung
"""

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


URL = "wss://api.openai.com/v1/realtime/translations?model=gpt-realtime-translate"
SAMPLE_RATE = 24000
CHUNK_FRAMES = 4800  


def receive(ws):
    message = ws.recv()
    if not message:
        raise RuntimeError("Connection ended before session.closed")
    event = json.loads(message)
    if event.get("type") == "error":
        error = event.get("error", {})
        raise RuntimeError(f"OpenAI: {error.get('message', error)}")
    return event


def wait_for(ws, event_type):
    while receive(ws).get("type") != event_type:
        pass


