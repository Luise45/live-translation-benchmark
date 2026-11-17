"""ElevenLabs-Anbindung für TTS und dateibasierte Audioausgabe."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


MODEL_ID = "eleven_flash_v2_5"


def synthesize_audio(text: str) -> bytes:
    """Erzeugt MP3-Audiodaten mit ElevenLabs Flash v2.5."""

    if not text.strip():
        raise ValueError("Der Text darf nicht leer sein.")

    api_key = (os.getenv("ELEVEN_API_KEY") or "").strip()
    voice_id = (os.getenv("VOICE_ID") or "").strip()

    if not api_key or not voice_id:
        raise RuntimeError(
            "ELEVEN_API_KEY oder VOICE_ID fehlt."
        )

    url = (
        "https://api.elevenlabs.io/v1/"
        f"text-to-speech/{voice_id}"
    )

    payload = json.dumps({
        "text": text,
        "model_id": MODEL_ID,
    }).encode("utf-8")

    request = Request(
        url,
        data=payload,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            audio = response.read()

    except HTTPError as error:
        response_body = error.read().decode(
            "utf-8", errors="replace"
        )

        error_code = "unknown"
        message = "Keine lesbare API-Fehlermeldung"

        try:
            error_data = json.loads(response_body)
        except json.JSONDecodeError:
            error_data = None

        if isinstance(error_data, dict):
            detail = error_data.get("detail")

            if isinstance(detail, dict):
                error_code = detail.get(
                    "code",
                    detail.get("status", "unknown"),
                )
                message = detail.get(
                    "message",
                    "Keine Fehlerbeschreibung",
                )
            elif isinstance(detail, str):
                message = detail

        raise RuntimeError(
            f"ElevenLabs HTTP {error.code} "
            f"({error_code}): {message}"
        ) from error

    if not audio:
        raise RuntimeError(
            "ElevenLabs hat keine Audiodaten zurückgegeben."
        )

    return audio


class ElevenLabsTTSProvider:
    """Stellt ElevenLabs über die interne TTS-Schnittstelle bereit."""

    name = "elevenlabs"

    @property
    def audio_format(self) -> str:
        return "mp3"

    def synthesize(self, text: str) -> bytes:
        return synthesize_audio(text)


def synthesize_mp3(text: str, output_path: str) -> str:
    """Erzeugt eine MP3-Datei und gibt deren Pfad zurück."""

    audio = synthesize_audio(text)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)

    return str(path)