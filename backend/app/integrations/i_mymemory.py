
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def translate_text(text: str) -> str:
    """Übersetzt deutschen Text mit MyMemory ins Englische."""

    if not text.strip():
        raise ValueError("Der Text darf nicht leer sein.")

    # MyMemory erlaubt maximal 500 UTF-8-Bytes pro Anfrage.
    if len(text.encode("utf-8")) > 500:
        raise ValueError(
            "Text ist zu lang für eine MyMemory-Anfrage."
        )

    params = urlencode({
        "q": text,
        "langpair": "de|en"
    })

    url = "https://api.mymemory.translated.net/get?" + params

    request = Request(
        url,
        headers={"User-Agent": "VIER-Working-Skeleton/1.0"}
    )

    with urlopen(request, timeout=30) as response:
        data = json.load(response)

    if int(data.get("responseStatus", 0)) != 200:
        raise RuntimeError(
            f"MyMemory-Fehler: {data.get('responseDetails')}"
        )

    if data.get("quotaFinished"):
        raise RuntimeError("MyMemory-Kontingent aufgebraucht.")

    translation = data["responseData"]["translatedText"]

    if not translation.strip():
        raise RuntimeError("Keine Übersetzung erhalten.")

    return translation
