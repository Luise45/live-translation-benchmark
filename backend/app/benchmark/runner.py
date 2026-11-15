"""
benchmark runnerr

purpose_koordiniert einen Benchmark-Durchlauf: lädt die gewählten Candidates, 
führt jeden Testfall (optimal mehrfach) über das gemeinsame Interface aus und 
speichert Ergebnisse und Fehler.

used by: 
- api/benchmark.py
- Kommandozeile (python -m app.benchmark.runner)

uses:
- core/interfaces.py, core/models.py
- candidates/* (nur ueber das Interface)

does not contain:
- provider-spezifisches Code
- scoring
"""

import argparse
import importlib
import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.core.interfaces import Candidate
from app.core.models import BenchmarkCase, BenchmarkConfig, RunRecord

#Name -> (Modul, Klasse). Import erst bei Bedarf,, dmit fehlende Abhängigkeit
# eines Candidates nicht den Runner blockiert
# TODO: später in candidates/registry.py auslagern, damit auch die API die Liste nutzen kann.
CANDIDATES: dict[str, tuple[str, str]] = {
    "openai_s2s": ("app.candidates.c_openai", "OpenAICandidate"),
    #"soniox": ("app.candidates.c_soniox", "<KLASSENNAME>"),
}

def available_candidates() -> list[str]:
    return sorted(CANDIDATES)


def load_candidate(name: str) -> Candidate:
    if name not in CANDIDATES:
        raise ValueError(f"Unknown candidate {name!r}. Available: {', '.join(CANDIDATES)}")
    module_name, class_name = CANDIDATES[name]
    return getattr(importlib.import_module(module_name), class_name)()

def run_benchmark(config: BenchmarkConfig) -> list[RunRecord]:
    run_dir = config.output_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    (run_dir / "audio").mkdir(parents=True, exist_ok=True)

    # Alle Candidates vorab laden: ein Fehler zeigt sich sofort
    candidates = {name: load_candidate(name) for name in config.candidates}

    records: list[RunRecord] = []
    for name, candidate in candidates.items():
        for case in config.cases:
            for repetition in range(1, config.repetitions + 1):
                record = _run_one(candidate, case, repetition, run_dir)
                records.append(record)
                _append_record(record, run_dir)
                print(f"[{'ERROR' if record.error else 'ok'}] {name} | {case.id} | rep {repetition}")
    return records

def _run_one(candidate: Candidate, case: BenchmarkCase, repetition: int, run_dir: Path) -> RunRecord:
    started_at = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    result, error, audio_file = None, None, None
    try: 
        result = candidate.translate(
        case.audio_path, 
        case.source_language, 
        case.target_language,
    )
        audio_file = f"audio/{candidate.name}__{case.id}__r{repetition}.wav"
        (run_dir / audio_file).write_bytes(result.translated_audio)
    except Exception as exc: #ein fehlögeschlagerern Fall soll Lauf nicht abbrechen
        error = f"{type(exc).__name__}: {exc}"
    wall_ms = (time.perf_counter() - start) * 1000.0
    return RunRecord(
        candidate=candidate.name, case_id=case.id, repetition=repetition, 
        started_at=started_at, runner_wall_time_ms=round(wall_ms, 1),
        result=result, error=error, audio_file=audio_file,
        )

def _append_record(record: RunRecord, run_dir: Path) -> None:
    data = asdict(record)
    if data["result"] is not None: 
        data["result"].pop("translated_audio", None) #! liegt als WAV in audio/ - passt mit bib?
    with (run_dir / "results.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the live translation benchmark")
    parser.add_argument("--candidates", nargs="+", required=True, choices=available_candidates())
    parser.add_argument("--audio", nargs="+", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()

    cases = [
        BenchmarkCase(id=p.stem, audio_path=p,
         source_language=args.source, target_language=args.target)
        for p in args.audio
    ]
    records = run_benchmark(BenchmarkConfig(
        candidates=args.candidates, cases=cases,
        repetitions=args.repetitions, output_dir=args.output_dir,
    ))
    failed = sum(1 for r in records if r.error)
    print(f"{len(records)} runs, {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()