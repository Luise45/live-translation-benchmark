import os

import deepl


def translate_text(text: str) -> str:
    api_key = os.getenv("DEEPL_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Umgebungsvariable fehlt: DEEPL_API_KEY"
        )

    client = deepl.DeepLClient(api_key)

    result = client.translate_text(
        text,
        source_lang="DE",
        target_lang="EN-US"
    )

    return result.text
