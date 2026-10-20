# Benchmark Candidates
This folder contains the complete solutions that are tested in the benchmark.
A candidate can use one or more integrations.

examples:
- Soniox Translation + Soniox TTS

Candidates should reuse existing integrations instead of implementing provider
API communication again.

Provider-specific API communication does not belong here.
It belongs in `integrations/`.