"""
shared data models for the benchmark

purpose:
defines common data structures used across the benchmark, for example
benchmark requests, results, latency values and errors

used by:
- API routes
- benchmark runner
- candidates
- integrations when provider responses are converted into our common format

does not contain:
- provider-specific API responses
- provider API calls
- FE logic
"""