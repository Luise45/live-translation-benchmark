"""
FastAPI application entry point.

Purpose:
Creates the backend web application.

Belongs here:
- application setup
- router registration
- health endpoint

Does NOT belong here:
- provider API implementation
- benchmark calculations
- API keys
"""

from fastapi import FastAPI


app = FastAPI(
    title="Live Translation Benchmark",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health check for local development and deployment."""
    return {"status": "ok"}