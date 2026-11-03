
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def synthesize_mp3(text: str, output_path: str) -> str:
    """Erzeugt mit ElevenLabs Flash v2.5 eine MP3-Datei."""

    api_key = (os.getenv("ELEVEN_API_KEY") or "").strip()
    voice_id = (os.getenv("VOICE_ID") or "").strip()

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

    # ElevenLabs Flash v2.5 verwenden
    payload = json.dumps({
        "text": text,
        "model_id": "eleven_flash_v2_5"
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

    try:
        with urlopen(request, timeout=120) as response:
            audio = response.read()

    except HTTPError as error:
        # Fehlermeldung der ElevenLabs-API auslesen
        response_body = error.read().decode(
            "utf-8", errors="replace"
        )

        try:
            error_data = json.loads(response_body)
            detail = error_data.get("detail", {})

            if isinstance(detail, dict):
                error_code = detail.get(
                    "code", detail.get("status", "unknown")
                )
                message = detail.get(
                    "message", "Keine Fehlerbeschreibung"
                )
            else:
                error_code = "unknown"
                message = str(detail)

        except json.JSONDecodeError:
            error_code = "unknown"
            message = "Keine lesbare API-Fehlermeldung"

        raise RuntimeError(
            f"ElevenLabs HTTP {error.code} "
            f"({error_code}): {message}"
        ) from error

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)

    return str(path)
