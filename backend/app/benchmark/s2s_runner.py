"""
Benchmark Runner für Speech-to-Speech-Candidates (Walking Skeleton)

purpose:
führt einen Candidate auf einer Audiodatei aus und speichert das Ergebnis
(übersetztes Audio + JSON mit Transkripten, Zeiten und Kosten).

Der Runner kennt nur die Candidate-Schnittstelle aus core/interfaces.py,
nichts Anbieter-Spezifisches.

Aufruf (aus dem Ordner backend/):
    python -m app.benchmark.s2s_runner ../testdata/de_Kunde_001_test-mono.wav \
        --candidate openai_s2s --source de --target en --output-dir ../results
"""

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from app.core.interfaces import Candidate, CandidateResult


def get_candidates() -> dict[str, type[Candidate]]:
    """Alle registrierten S2S-Candidates (Name -> Klasse)."""
    from app.candidates.c_openai import OpenAICandidate

    return {cls.name: cls for cls in (OpenAICandidate,)}


def run_candidate(
    candidate: Candidate,
    audio_path: Path,
    source_language: str,
    target_language: str,
    output_dir: Path,
) -> tuple[CandidateResult, Path, Path]:
    """Führt einen Candidate aus und speichert Audio + JSON. Gibt (result, wav, json) zurück."""
    result = candidate.translate(Path(audio_path), source_language, target_language)

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{Path(audio_path).stem}__{candidate.name}__{result.target_language}"
    wav_path = output_dir / f"{stem}.wav"
    json_path = output_dir / f"{stem}.json"

    wav_path.write_bytes(result.translated_audio)

    data = asdict(result)
    data.pop("translated_audio")  # Bytes gehören nicht ins JSON
    data["input_file"] = str(audio_path)
    data["translated_audio_file"] = str(wav_path)
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return result, wav_path, json_path


def main() -> None:
    candidates = get_candidates()
    parser = argparse.ArgumentParser(description="Run one S2S candidate on one audio file")
    parser.add_argument("input", type=Path, help="WAV file (any sample rate / channels, PCM)")
    parser.add_argument("--candidate", default="openai_s2s", choices=sorted(candidates))
    parser.add_argument("--source", default="de", help="source language code (default: de)")
    parser.add_argument("--target", default="en", help="target language code (default: en)")
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()

    candidate = candidates[args.candidate]()
    try:
        result, wav_path, json_path = run_candidate(
            candidate, args.input, args.source, args.target, args.output_dir,
        )
    except Exception as exc:  # Runner soll sauber melden, nicht abstürzen
        parser.exit(1, f"[{candidate.name}] failed: {type(exc).__name__}: {exc}\n")

    print(f"Candidate:      {result.candidate} ({result.model})")
    print(f"Source:         {result.source_transcript}")
    print(f"Translation:    {result.translated_transcript}")
    print(f"Processing:     {result.total_processing_time_ms:.0f} ms "
          f"for {result.input_audio_duration_s:.1f} s audio")
    print(f"Cost (est.):    {result.cost_usd:.4f} USD")
    print(f"Audio saved to: {wav_path.resolve()}")
    print(f"Result saved to:{json_path.resolve()}")


if __name__ == "__main__":
    main()
