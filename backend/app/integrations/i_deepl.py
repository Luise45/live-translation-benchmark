
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

