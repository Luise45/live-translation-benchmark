# Background Noise for Single-Factor Tests (XY-44)

This folder contains open-source background noise files for simulated audio stress tests.
The actual audio files (.wav, .zip) are not stored in the Git repository to keep the repository size small. They are downloaded locally via a script.

## Sources and Licenses

### 1. DEMAND Dataset
- **Source:** https://zenodo.org/records/1227121
- **License:** CC BY-SA 3.0 Unported
- **Authors:** Thiemann, J., Ito, N., & Vincent, E. (2013)

### 2. MS-SNSD (Microsoft Scalable Noisy Speech Dataset)
- **Source:** https://github.com/microsoft/MS-SNSD
- **License:** MIT License (Copyright (c) Microsoft Corporation)
- **Paper:** https://arxiv.org/pdf/1909.08050

### 3. CHiME-3 Background Noise (Alternative)
- **Source:** https://zenodo.org/records/23571516
- **License:** CC BY 4.0 International

### 4. Freesound.org (Supplement)
- **Source:** https://freesound.org/
- **License:** CC0 (Public Domain)

## Usage
The files are **not** pre-mixed. Mixing is done dynamically by the benchmark script at runtime (see Confluence concept: XY-44).