"""
shared interfaces for all benchmark candidates.

purpose:
defines what every benchmark candidate must provide so the benchmark runner
can use all candidates in the same way.

used by:
- benchmark/runner.py
- candidate implementations

does not contain:
- provider API calls
- provider-specific response formats
- benchmark scoring
"""