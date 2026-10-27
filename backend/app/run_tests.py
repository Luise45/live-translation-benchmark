
from pathlib import Path
from app.benchmark.runner import run_benchmark
from app.candidates import c_openai_s2s

PROJECT_ROOT = Path(__file__).resolve().parents[2]
audio_path = (
    PROJECT_ROOT
    / "testdata/de_Kunde_001_test-mono-24k.wav"
)

result = run_benchmark(
    candidate=c_openai_s2s,
    audio_path=audio_path,
    source_language="de",
    target_language="en",
)

print("\nÜbersetztes Transkript:")
print(result.translated_transcript)

print("\nZeit bis zum ersten Audio (ms):")
print(result.time_to_first_audio_ms, "ms")
