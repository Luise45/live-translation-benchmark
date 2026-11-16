"""DeepL-Anbindung für einzelne Übersetzungen und die Streaming-Kaskade."""

import os

import deepl


def translate_text(
    text: str,
    target_lang: str = "EN-US",
    source_lang: str = "DE",
) -> str:
    """Übersetzt einen Text mit DeepL."""

    api_key = (os.getenv("DEEPL_API_KEY") or "").strip()

    if not api_key:
        raise RuntimeError(
            "Umgebungsvariable fehlt: DEEPL_API_KEY"
        )

    client = deepl.DeepLClient(
        api_key,
        timeout_s=10,
        max_retries=0,
    )

    result = client.translate_text(
        text,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    return result.text


class DeepLTranslationProvider:
    """Stellt DeepL über die gemeinsame Provider-Schnittstelle bereit."""

    name = "deepl"

    def translate(
        self,
        text: str,
        *,
        source_lang: str,
        target_lang: str,
    ) -> str:
        return translate_text(
            text,
            source_lang=source_lang,
            target_lang=target_lang,
        )

