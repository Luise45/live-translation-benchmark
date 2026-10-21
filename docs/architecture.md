## Application Flow

FE
→ API
→ Benchmark Runner
→ Candidate
→ Integration
→ External Provider

## Shared Core

`core/` contains shared interfaces and data models used by the benchmark,
candidates and integrations.


api/
= what does the FE ask the BE to do?

benchmark/
= how is a benchmark run executed?

candidates/
= which complete solutions are tested?

integrations/
= how do we communicate with external providers?

core/
= which shared interfaces and data models are used across the benchmark?