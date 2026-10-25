
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
from backend.app.integrations.i_mymemory import translate_text
from backend.app.integrations.i_elevenlabs import synthesize_mp3


def run_cascade(audio_path: str):
    """Führt die vollständige Übersetzungskaskade aus."""

    audio = Path(audio_path)

    if not audio.is_file():
        raise FileNotFoundError(f"Audiodatei fehlt: {audio}")

    for key in ("DEEPGRAM_API_KEY", "ELEVEN_API_KEY", "VOICE_ID"):
        if not os.getenv(key):
            raise RuntimeError(f"Umgebungsvariable fehlt: {key}")

    output_dir = Path("results/cascade")
    output_dir.mkdir(parents=True, exist_ok=True)

    benchmark = BenchmarkResult(input_audio=str(audio))
    total_start = time.perf_counter()

    # 1. Speech-to-Text
    print("\n1. Deepgram transkribiert ...")

    stt_result = DeepgramSTT().transcribe(str(audio))
    benchmark.steps.append(stt_result)

    german_text = stt_result.output
    if not german_text.strip():
        raise RuntimeError("Deepgram hat keinen Text erkannt.")

    print("Deutsch:", german_text)

    # 2. Translation
    print("\n2. MyMemory übersetzt ...")

    start = time.perf_counter()
    english_text = translate_text(german_text)
    translation_latency = time.perf_counter() - start

    benchmark.steps.append(StageResult(
        stage="translation",
        model="mymemory",
        output=english_text,
        latency_seconds=translation_latency
    ))

    print("Englisch:", english_text)

    # 3. Text-to-Speech
    print("\n3. ElevenLabs erzeugt Audio ...")

    mp3_path = output_dir / "uebersetzung.mp3"

    start = time.perf_counter()
    synthesize_mp3(english_text, str(mp3_path))
    tts_latency = time.perf_counter() - start

    benchmark.steps.append(StageResult(
        stage="tts",
        model="elevenlabs_multilingual_v2",
        output=str(mp3_path),
        latency_seconds=tts_latency
    ))

    # 4. Optional: MP3 auf dem Mac in WAV umwandeln
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

            conversion_latency = time.perf_counter() - start
            wav_created = True

        except subprocess.CalledProcessError as error:
            print("WAV-Konvertierung fehlgeschlagen:", error.stderr)

    total_latency = time.perf_counter() - total_start

    # 5. Ergebnisse speichern
    result_data = {
        "input_audio": str(audio),
        "original_transcript": german_text,
        "translated_transcript": english_text,
        "audio_mp3": str(mp3_path),
        "audio_wav": str(wav_path) if wav_created else None,
        "steps": [asdict(step) for step in benchmark.steps],
        "pipeline_latency_seconds": benchmark.total_latency_seconds,
        "wav_conversion_seconds": conversion_latency,
        "end_to_end_seconds": total_latency
    }

    json_path = output_dir / "ergebnis.json"
    json_path.write_text(
        json.dumps(result_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\n=== BENCHMARK-ERGEBNIS ===")

    for step in benchmark.steps:
        print(f"{step.stage}: {step.latency_seconds:.3f} s")

    print(f"Gesamtdauer: {total_latency:.3f} s")
    print(f"JSON: {json_path}")
    print(f"MP3: {mp3_path}")

    if wav_created:
        print(f"WAV: {wav_path}")

    return result_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", help="Pfad zur WAV-Datei")
    args = parser.parse_args()

    run_cascade(args.audio)
