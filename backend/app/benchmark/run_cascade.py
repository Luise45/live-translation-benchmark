
import argparse
import json
import os
import shutil
import subprocess
import time

from dataclasses import asdict
from pathlib import Path

from backend.app.candidates.c_deepgram import DeepgramSTT
from backend.app.core.models import BenchmarkResult, StageResult
from backend.app.integrations.i_deepl import (
    translate_text as translate_text_deepl
)
from backend.app.integrations.i_elevenlabs import synthesize_mp3


# Verfügbare Modelle für die Kaskade

STT_MODELS = {
    "deepgram": DeepgramSTT
}

TRANSLATION_MODELS = {
    "deepl": translate_text_deepl
}

TTS_MODELS = {
    "elevenlabs": synthesize_mp3
}

# Genaue Modellversionen für die Benchmark-Ergebnisse
TTS_MODEL_IDS = {
    "elevenlabs": "eleven_flash_v2_5"
}


def run_cascade(
    audio_path: str,
    stt_model: str = "deepgram",
    translation_model: str = "deepl",
    tts_model: str = "elevenlabs"
):
    """Führt die vollständige Übersetzungskaskade aus."""

    audio = Path(audio_path)

    if not audio.is_file():
        raise FileNotFoundError(
            f"Audiodatei fehlt: {audio}"
        )

    # Benötigte API-Schlüssel prüfen
    for key in (
        "DEEPGRAM_API_KEY",
        "DEEPL_API_KEY",
        "ELEVEN_API_KEY",
        "VOICE_ID"
    ):
        if not os.getenv(key):
            raise RuntimeError(
                f"Umgebungsvariable fehlt: {key}"
            )

    # Ordner für Ergebnisse erstellen
    output_dir = Path("results/cascade")
    output_dir.mkdir(parents=True, exist_ok=True)

    benchmark = BenchmarkResult(
        input_audio=str(audio)
    )

    total_start = time.perf_counter()

    # ---------------------------------------
    # 1. Speech-to-Text mit Deepgram Nova-3
    # ---------------------------------------

    print(f"\n1. {stt_model} transkribiert ...")

    stt_result = STT_MODELS[stt_model]().transcribe(
        str(audio)
    )

    benchmark.steps.append(stt_result)

    german_text = stt_result.output

    if not german_text.strip():
        raise RuntimeError(
            f"{stt_model} hat keinen Text erkannt."
        )

    print("Deutsch:", german_text)

    # ---------------------------------------
    # 2. Machine Translation mit DeepL
    # ---------------------------------------

    print(f"\n2. {translation_model} übersetzt ...")

    start = time.perf_counter()

    english_text = TRANSLATION_MODELS[translation_model](
        german_text
    )

    translation_latency = time.perf_counter() - start

    if not english_text.strip():
        raise RuntimeError(
            f"{translation_model} hat keinen Text übersetzt."
        )

    benchmark.steps.append(
        StageResult(
            stage="translation",
            model=translation_model,
            output=english_text,
            latency_seconds=translation_latency
        )
    )

    print("Englisch:", english_text)

    # ---------------------------------------
    # 3. Text-to-Speech mit ElevenLabs Flash v2.5
    # ---------------------------------------

    print(f"\n3. {tts_model} erzeugt Audio ...")

    mp3_path = output_dir / "uebersetzung.mp3"

    # Genaue Modellversion bestimmen
    tts_model_id = TTS_MODEL_IDS[tts_model]

    start = time.perf_counter()

    TTS_MODELS[tts_model](
        english_text,
        str(mp3_path)
    )

    tts_latency = time.perf_counter() - start

    benchmark.steps.append(
        StageResult(
            stage="tts",
            model=tts_model_id,
            output=str(mp3_path),
            latency_seconds=tts_latency
        )
    )

    # ---------------------------------------
    # 4. Optional: MP3 in WAV umwandeln
    # ---------------------------------------

    wav_path = output_dir / "uebersetzung.wav"
    wav_created = False
    conversion_latency = None

    if shutil.which("afconvert"):
        try:
            if wav_path.exists():
                wav_path.unlink()

            start = time.perf_counter()

            subprocess.run(
                [
                    "afconvert",
                    "-f", "WAVE",
                    "-d", "LEI16",
                    str(mp3_path),
                    str(wav_path)
                ],
                check=True,
                capture_output=True,
                text=True
            )

            conversion_latency = (
                time.perf_counter() - start
            )

            wav_created = True

        except subprocess.CalledProcessError as error:
            print(
                "WAV-Konvertierung fehlgeschlagen:",
                error.stderr
            )

    total_latency = time.perf_counter() - total_start

    # ---------------------------------------
    # 5. Benchmark-Ergebnisse speichern
    # ---------------------------------------

    result_data = {
        "input_audio": str(audio),
        "stt_model": stt_model,
        "translation_model": translation_model,
        "tts_model": tts_model,
        "tts_model_id": tts_model_id,
        "original_transcript": german_text,
        "translated_transcript": english_text,
        "audio_mp3": str(mp3_path),
        "audio_wav": (
            str(wav_path) if wav_created else None
        ),
        "steps": [
            asdict(step) for step in benchmark.steps
        ],
        "pipeline_latency_seconds": (
            benchmark.total_latency_seconds
        ),
        "wav_conversion_seconds": conversion_latency,
        "end_to_end_seconds": total_latency
    }

    json_path = output_dir / "ergebnis.json"

    json_path.write_text(
        json.dumps(
            result_data,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # ---------------------------------------
    # 6. Benchmark-Ergebnisse anzeigen
    # ---------------------------------------

    print("\n=== BENCHMARK-ERGEBNIS ===")

    for step in benchmark.steps:
        print(
            f"{step.stage} ({step.model}): "
            f"{step.latency_seconds:.3f} s"
        )

    print(f"Gesamtdauer: {total_latency:.3f} s")

    print(f"JSON: {json_path}")
    print(f"MP3: {mp3_path}")

    if wav_created:
        print(f"WAV: {wav_path}")

    return result_data


# ---------------------------------------
# 7. Kommandozeilenargumente
# ---------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark für kaskadierte Sprachübersetzung"
    )

    parser.add_argument(
        "audio",
        help="Pfad zur WAV-Datei"
    )

    parser.add_argument(
        "--stt",
        choices=list(STT_MODELS.keys()),
        default="deepgram"
    )

    parser.add_argument(
        "--translation",
        choices=list(TRANSLATION_MODELS.keys()),
        default="deepl"
    )

    parser.add_argument(
        "--tts",
        choices=list(TTS_MODELS.keys()),
        default="elevenlabs"
    )

    args = parser.parse_args()

    run_cascade(
        audio_path=args.audio,
        stt_model=args.stt,
        translation_model=args.translation,
        tts_model=args.tts
    )
