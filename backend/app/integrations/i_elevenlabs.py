
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


def synthesize_mp3(text: str, output_path: str) -> str:
    """Erzeugt mit ElevenLabs eine MP3-Datei."""

    api_key = os.getenv("ELEVEN_API_KEY")
    voice_id = os.getenv("VOICE_ID")

    if not api_key or not voice_id:
        raise RuntimeError(
            "ELEVEN_API_KEY oder VOICE_ID fehlt."
        )

    if not text.strip():
        raise ValueError("Der Text darf nicht leer sein.")

    url = (
        "https://api.elevenlabs.io/v1/"
        f"text-to-speech/{voice_id}"
    )

    payload = json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2"
    }).encode("utf-8")

    request = Request(
        url,
        data=payload,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        },
        method="POST"
    )

    with urlopen(request, timeout=120) as response:
        audio = response.read()

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)

    return str(path)
