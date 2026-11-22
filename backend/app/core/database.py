
import os
from pathlib import Path
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv

# Pfad zum Hauptordner des Projekts
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Zugangsdaten aus der .env laden
load_dotenv(PROJECT_ROOT / ".env")


@contextmanager
def get_db_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL fehlt in der .env-Datei."
        )

    with psycopg.connect(
        database_url,
        sslmode="require",
        connect_timeout=10
    ) as connection:
        yield connection
