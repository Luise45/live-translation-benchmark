import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen


def transcribe_wav(wav_path):
    """Wandelt eine deutsche WAV-Datei mit Deepgram in Text um."""

    api_key = os.getenv("DEEPGRAM_API_KEY")

    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY ist nicht gesetzt.")

    audio = Path(wav_path).read_bytes()

    url = (
        "https://api.deepgram.com/v1/listen"
        "?model=nova-3&language=de&smart_format=true"
    )

    request = Request(
        url,
        data=audio,
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": "audio/wav",
        },
        method="POST",
    )

    start = time.perf_counter()

    with urlopen(request, timeout=60) as response:
        result = json.load(response)

    latency = time.perf_counter() - start

    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]

    return transcript, latency
