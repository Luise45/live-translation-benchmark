"""
OpenAI Speech-to-Speech benchmark candidate (gpt-realtime-translate)

purpose:
verbindet die Benchmark-Welt (core/interfaces.py) mit der OpenAI-Welt
(integrations/i_openai.py). Die Datei macht vier Dinge:

1. Audio ins Format bringen, das OpenAI verlangt (24 kHz, mono, PCM16 WAV)
2. Sprachcodes übersetzen (Benchmark-Code -> OpenAI-Code)
3. i_openai.translate() aufrufen
4. Rohergebnis in das einheitliche CandidateResult umbauen (+ Kosten)

used by:
- benchmark/s2s_runner.py

uses:
- integrations/i_openai.py  (die eigentliche API-Kommunikation)
- core/interfaces.py, core/models.py

does not contain:
- WebSocket- / API-Code (gehört in i_openai.py)
- Scoring
"""

import tempfile
import time
import wave
from math import gcd
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from scipy.signal import resample_poly

from app.core.interfaces import Candidate, CandidateResult


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

MODEL = "gpt-realtime-translate"

# Format, das i_openai.translate() erwartet (siehe i_openai.SAMPLE_RATE)
TARGET_SAMPLE_RATE = 24000
TARGET_CHANNELS = 1
TARGET_SAMPWIDTH = 2  # PCM16 = 2 Bytes pro Messwert

# Preise in USD pro Minute Audio (Stand Nov 2026, bitte bei Bedarf prüfen:
# https://developers.openai.com/api/docs/models/gpt-realtime-translate)
PRICE_TRANSLATE_PER_MIN_USD = 0.034
# i_openai aktiviert zusätzlich die Quell-Transkription mit gpt-realtime-whisper.
# Dieser Preis stammt aus einer Drittquelle -> im OpenAI-Pricing gegenprüfen.
PRICE_TRANSCRIPTION_PER_MIN_USD = 0.017

# Zielsprachen, die gpt-realtime-translate ausgeben kann (Eingangssprache wird
# von OpenAI automatisch erkannt, 70+ Sprachen).
SUPPORTED_TARGET_LANGUAGES = {
    "de", "en", "es", "fr", "it", "pt", "ru",
    "zh", "ja", "ko", "hi", "id", "vi",
}

# Benchmark-Code / Name -> OpenAI-Code (ISO 639-1, zweistellig)
_LANGUAGE_ALIASES = {
    # ISO 639-2/3
    "deu": "de", "ger": "de", "eng": "en", "spa": "es", "fra": "fr", "fre": "fr",
    "ita": "it", "por": "pt", "rus": "ru", "zho": "zh", "chi": "zh", "cmn": "zh",
    "jpn": "ja", "kor": "ko", "hin": "hi", "ind": "id", "vie": "vi",
    "tur": "tr", "ara": "ar", "pol": "pl", "nld": "nl", "dut": "nl",
    # ausgeschriebene Namen (EN / DE)
    "german": "de", "deutsch": "de",
    "english": "en", "englisch": "en",
    "spanish": "es", "spanisch": "es",
    "french": "fr", "französisch": "fr", "franzoesisch": "fr",
    "italian": "it", "italienisch": "it",
    "portuguese": "pt", "portugiesisch": "pt",
    "russian": "ru", "russisch": "ru",
    "chinese": "zh", "chinesisch": "zh", "mandarin": "zh",
    "japanese": "ja", "japanisch": "ja",
    "korean": "ko", "koreanisch": "ko",
    "hindi": "hi",
    "indonesian": "id", "indonesisch": "id",
    "vietnamese": "vi", "vietnamesisch": "vi",
    "turkish": "tr", "türkisch": "tr", "tuerkisch": "tr",
    "arabic": "ar", "arabisch": "ar",
}


# ---------------------------------------------------------------------------
# 2. Sprachcodes übersetzen
# ---------------------------------------------------------------------------

def to_openai_language(code: str) -> str:
    """
    Wandelt einen Benchmark-Sprachcode in den OpenAI-Code um.

    Beispiele: "de-DE" -> "de", "en_US" -> "en", "deu" -> "de",
    "German" -> "de", "zh-Hans-CN" -> "zh".
    """
    if not code or not code.strip():
        raise ValueError("Language code must not be empty")
    normalized = code.strip().lower().replace("_", "-")
    if normalized in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[normalized]
    primary = normalized.split("-")[0]
    primary = _LANGUAGE_ALIASES.get(primary, primary)
    if len(primary) != 2 or not primary.isalpha():
        raise ValueError(f"Unknown language code: {code!r}")
    return primary


def to_openai_target_language(code: str) -> str:
    """Wie to_openai_language, prüft aber zusätzlich, ob OpenAI dahin übersetzen kann."""
    language = to_openai_language(code)
    if language not in SUPPORTED_TARGET_LANGUAGES:
        raise ValueError(
            f"Target language {code!r} ({language}) is not supported by {MODEL}. "
            f"Supported: {', '.join(sorted(SUPPORTED_TARGET_LANGUAGES))}"
        )
    return language


# ---------------------------------------------------------------------------
# 1. Audio ins OpenAI-Format bringen
# ---------------------------------------------------------------------------

def _read_wav_as_float(path: Path) -> tuple[np.ndarray, int, dict]:
    """Liest eine PCM-WAV (8/16/24/32 Bit, beliebig viele Kanäle) als float32 [-1, 1], mono."""
    with wave.open(str(path), "rb") as audio:
        channels = audio.getnchannels()
        sampwidth = audio.getsampwidth()
        rate = audio.getframerate()
        comptype = audio.getcomptype()
        raw = audio.readframes(audio.getnframes())

    if comptype != "NONE":
        raise ValueError(f"Compressed WAV ({comptype}) is not supported")
    if not raw:
        raise ValueError("Input recording is empty")

    if sampwidth == 1:  # 8 Bit ist unsigned
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sampwidth == 2:
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sampwidth == 3:  # 24 Bit: 3 Bytes auf int32 auffüllen
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        ints = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        ints = np.where(ints & 0x800000, ints - 0x1000000, ints)
        samples = ints.astype(np.float32) / 8388608.0
    elif sampwidth == 4:
        samples = (np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0).astype(np.float32)
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth} bytes")

    # Stereo / Mehrkanal -> mono (Mittelwert der Kanäle)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    info = {"sample_rate": rate, "channels": channels, "sample_width_bytes": sampwidth}
    return samples, rate, info


def prepare_audio(input_path: Path, work_dir: Path) -> tuple[Path, dict]:
    """
    Sorgt dafür, dass OpenAI eine 24 kHz / mono / PCM16 WAV bekommt.

    Ist die Datei schon im richtigen Format, wird sie direkt verwendet.
    Sonst wird eine konvertierte Kopie in work_dir geschrieben.
    Rückgabe: (Pfad für OpenAI, Infos zur Konvertierung)
    """
    with wave.open(str(input_path), "rb") as audio:
        params = (audio.getnchannels(), audio.getsampwidth(),
                  audio.getframerate(), audio.getcomptype())
        n_frames = audio.getnframes()
    if n_frames == 0:
        raise ValueError("Input recording is empty")

    if params == (TARGET_CHANNELS, TARGET_SAMPWIDTH, TARGET_SAMPLE_RATE, "NONE"):
        return input_path, {"converted": False, "original_sample_rate": TARGET_SAMPLE_RATE,
                            "original_channels": 1, "original_sample_width_bytes": 2}

    samples, rate, info = _read_wav_as_float(input_path)

    if rate != TARGET_SAMPLE_RATE:
        # Polyphase-Resampling (mit Anti-Aliasing-Filter), z.B. 48k -> 24k: up=1, down=2
        g = gcd(rate, TARGET_SAMPLE_RATE)
        samples = resample_poly(samples, TARGET_SAMPLE_RATE // g, rate // g)

    pcm16 = (np.clip(samples, -1.0, 1.0) * 32767.0).round().astype("<i2")

    converted_path = work_dir / "input_24k_mono.wav"
    with wave.open(str(converted_path), "wb") as out:
        out.setnchannels(TARGET_CHANNELS)
        out.setsampwidth(TARGET_SAMPWIDTH)
        out.setframerate(TARGET_SAMPLE_RATE)
        out.writeframes(pcm16.tobytes())

    return converted_path, {
        "converted": True,
        "original_sample_rate": info["sample_rate"],
        "original_channels": info["channels"],
        "original_sample_width_bytes": info["sample_width_bytes"],
    }


def _wav_duration_s(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


# ---------------------------------------------------------------------------
# 4. Kosten
# ---------------------------------------------------------------------------

def estimate_cost_usd(input_duration_s: float, with_transcription: bool = True) -> float:
    """
    Kosten werden nach Audiodauer abgerechnet. Da i_openai das Audio in Echtzeit
    streamt, entspricht die Session-Dauer ungefähr der Dauer des Eingangs-Audios.
    """
    price = PRICE_TRANSLATE_PER_MIN_USD
    if with_transcription:
        price += PRICE_TRANSCRIPTION_PER_MIN_USD
    return round(input_duration_s / 60.0 * price, 6)


# ---------------------------------------------------------------------------
# .env laden (OPENAI_API_KEY), gleiche Suche wie in i_openai.main()
# ---------------------------------------------------------------------------

def _load_env() -> None:
    here = Path(__file__).resolve()
    for directory in (here.parent, *here.parents):
        if (directory / ".env").is_file():
            load_dotenv(directory / ".env", override=False)
            return


# ---------------------------------------------------------------------------
# Der Candidate
# ---------------------------------------------------------------------------

class OpenAICandidate(Candidate):
    """OpenAI gpt-realtime-translate als Speech-to-Speech-Candidate."""

    name = "openai_s2s"
    provider = "openai"
    architecture = "s2s"

    def __init__(self) -> None:
        _load_env()

    def translate(
        self,
        audio_path: Path,
        source_language: str,
        target_language: str,
    ) -> CandidateResult:
        # erst hier importieren, damit der Runner Candidates auflisten kann,
        # auch wenn websocket-client (noch) nicht installiert ist
        from app.integrations import i_openai

        audio_path = Path(audio_path)
        if not audio_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # 2. Sprachcodes übersetzen.
        # Die Quellsprache erkennt OpenAI selbst; wir normalisieren sie nur fürs Ergebnis.
        openai_source = to_openai_language(source_language)
        openai_target = to_openai_target_language(target_language)

        with tempfile.TemporaryDirectory(prefix="c_openai_") as tmp:
            work_dir = Path(tmp)

            # 1. Audio ins OpenAI-Format bringen
            prepared_path, conversion = prepare_audio(audio_path, work_dir)
            input_duration_s = _wav_duration_s(prepared_path)
            output_path = work_dir / "translated.wav"

            # 3. i_openai.translate() aufrufen (Zeit messen)
            start = time.perf_counter()
            source_transcript, translated_transcript = i_openai.translate(
                prepared_path, output_path, openai_target,
            )
            total_ms = (time.perf_counter() - start) * 1000.0

            translated_audio = output_path.read_bytes()
            output_duration_s = _wav_duration_s(output_path)

        # 4. Rohergebnis -> CandidateResult
        return CandidateResult(
            provider=self.provider,
            architecture=self.architecture,
            source_language=openai_source,
            target_language=openai_target,
            source_transcript=(source_transcript or "").strip() or None,
            translated_transcript=(translated_transcript or "").strip() or None,
            translated_audio=translated_audio,
            # i_openai.translate() liefert (noch) keinen Zeitpunkt des ersten Audio-Chunks
            time_to_first_audio_ms=None,
            total_processing_time_ms=round(total_ms, 1),
            candidate=self.name,
            model=MODEL,
            input_audio_duration_s=round(input_duration_s, 3),
            output_audio_duration_s=round(output_duration_s, 3),
            output_sample_rate=i_openai.SAMPLE_RATE,
            cost_usd=estimate_cost_usd(input_duration_s),
            metadata={
                "audio_conversion": conversion,
                "requested_source_language": source_language,
                "requested_target_language": target_language,
                "cost_basis": (
                    f"{PRICE_TRANSLATE_PER_MIN_USD} USD/min translate + "
                    f"{PRICE_TRANSCRIPTION_PER_MIN_USD} USD/min transcription, "
                    "based on input audio duration"
                ),
            },
        )
