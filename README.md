






## Architecture

The benchmark uses a provider-independent candidate architecture so different
live-translation solutions can be evaluated through the same benchmark runner.

See [docs/architecture.md](docs/architecture.md) for the current architecture decisions.

See [docs/benchmark-methodology.md](docs/benchmark-methodology.md) for the benchmark methodology. 















## License

This project is licensed under the Apache License 2.0.
See the [LICENSE](LICENSE) file for details.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for documented third-party components.

Third-party libraries, SDKs, APIs, models, and datasets may be subject
to their own licenses and terms.


## Backend development

Use `app.*` imports consistently. Start modules from `backend`, matching the
central runner. Pytest's `pythonpath = ["."]` points to this same backend directory.
From the repository root:

```sh
uv sync --locked --project backend
cd backend
uv run --locked python -m app.benchmark.runner --help
uv run --locked python -m pytest tests --ignore=tests/test_c_openai_integration.py
uv run --locked python -m app.integrations.i_deepgram_streaming ../testdata/de_Kunde_001_test.wav
```

Export the provider credentials in the terminal before a live streaming run.
The real OpenAI integration test is excluded above because it can call the API
when an API key is present. The separate database connection script is also a
live check, not part of this command.

### Dependency policy

`pyproject.toml` specifies allowed versions; the committed `uv.lock` pins exact
versions for reproducible runs. Use `uv sync --locked` rather than mixing manual
pip installs into that environment. After editing requirements, regenerate with
`uv lock --project backend` from the repository root.

DeepL requires `>=1.33.0,<2.0` for the per-client timeout and retry configuration.
DeepL, NumPy and pytest currently have explicit major-version bounds. Other
requirements retain their existing minimum versions; their exact versions are
fixed by the lockfile. An absent upper bound is not a claim that every future
version is compatible: dependency upgrades require tests and review. Avoid
inventing upper bounds without evidence of an incompatibility.

`psycopg[binary]` is the PostgreSQL driver used for the Supabase database connection.
The binary extra provides native dependencies without a local compiler setup.
Database credentials come from `DATABASE_URL`, never from the dependency files.

### Streaming segmentation and timing

This implementation translates every non-empty `is_final` segment immediately.
It does not accumulate segments until `speech_final`. This reduces waiting but
can split sentences and lose context for translation. `speech_final` signals a
pause detected by Deepgram and is retained in the output; it is not a guarantee
of a grammatical sentence boundary. For complete utterances, concatenate final
segments until `speech_final` (see [Deepgram's explanation](https://developers.deepgram.com/docs/understand-endpointing-interim-results)).

Each streaming translation worker owns one reusable DeepL client and closes it
when the worker exits, including on failure. Separate runs get separate clients.
The first segment's `translation_seconds` includes lazy client initialization and
the first request's connection setup. Later segments can reuse the HTTP session;
there is no process-wide warmed cache shared between benchmark runs. The instance
is intended for sequential use by one worker; revisit thread safety before sharing
it between concurrent workers.
