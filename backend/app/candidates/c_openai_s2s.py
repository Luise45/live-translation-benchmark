
from pathlib import Path

from app.core.models import TranslationResult
from app.integrations.i_openai import translate


def run(
    audio_path: Path,
    source_language: str = "de",
    target_language: str = "en",
) -> TranslationResult:
    print("Start von OpenAI Übersetzung..")

    result = translate(
        audio_path=audio_path, source_language=source_language, target_language=target_language,
    )

    print("OpenAI Übersetzung fertig")

    return result
