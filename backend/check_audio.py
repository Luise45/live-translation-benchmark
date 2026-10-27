import wave
# das Skript ist nutzbar um die Audiodatein zu prüfen.S
INPUT_FILE = "testdata/de_Kunde_001_test-mono-24k.wav"

with wave.open(str(INPUT_FILE), "rb") as audio:
    print("File:", INPUT_FILE)
    print("Channels:", audio.getnchannels())
    print("Sample rate:", audio.getframerate())
    print("Sample width:", audio.getsampwidth())
    print("Compression:", audio.getcomptype())

    if (
        audio.getnchannels() != 1
        or audio.getsampwidth() != 2
        or audio.getframerate() != 24000
        or audio.getcomptype() != "NONE"
    ):
        raise ValueError(
            "Input must be 24 kHz, mono, PCM16 WAV"
        )