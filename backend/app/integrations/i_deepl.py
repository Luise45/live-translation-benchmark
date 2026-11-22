"""DeepL translation with one reusable client per streaming run."""

import os

import deepl


class DeepLTranslator:
    """Owns a client for sequential calls from one translation worker.

    Initialization is lazy: its cost is included in the first translation.
    Do not share this instance between concurrent workers without checking
    the SDK's thread-safety guarantees.
    """

    def __init__(self) -> None:
        self._client: deepl.DeepLClient | None = None

    def translate(
        self, text: str, target_lang: str = "EN-US", source_lang: str = "DE"
    ) -> str:
        if self._client is None:
            api_key = (os.getenv("DEEPL_API_KEY") or "").strip()
            if not api_key:
                raise RuntimeError("Umgebungsvariable fehlt: DEEPL_API_KEY")
            self._client = deepl.DeepLClient(
                api_key, timeout_s=10, max_retries=0
            )

        result = self._client.translate_text(
            text, source_lang=source_lang, target_lang=target_lang
        )
        return result.text

    def close(self) -> None:
        """Release the HTTP session after the worker has finished."""
        if self._client is not None:
            self._client.close()
            self._client = None


def translate_text(
    text: str, target_lang: str = "EN-US", source_lang: str = "DE"
) -> str:
    """Translate a standalone text; streaming reuses DeepLTranslator instead."""
    translator = DeepLTranslator()
    try:
        return translator.translate(text, target_lang, source_lang)
    finally:
        translator.close()
