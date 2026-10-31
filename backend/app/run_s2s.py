
from pathlib import Path
from app.benchmark.runner import run_benchmark
from app.candidates import c_openai_s2s
# den root folder finden egal wo der command ausgeführt wird
PROJECT_ROOT = Path(__file__).resolve().parents[2]
audio_path = (
    PROJECT_ROOT
    / "testdata/de_Kunde_001_test-mono-24k.wav"
)
# benchmark ausführen und Ergebnis in result speichern
result = run_benchmark(
    candidate=c_openai_s2s,
    audio_path=audio_path,
    source_language="de",
    target_language="en",
)
# druck für die command line
print("\nÜbersetztes Transkript:")
print(result.translated_transcript)

print("\nZeit bis zum ersten Audio (ms):")
print(result.time_to_first_audio_ms, "ms")
 