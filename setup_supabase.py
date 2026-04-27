from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg
from dotenv import load_dotenv


def sanitize_postgres_dsn(dsn: str) -> str:
    parsed = urlsplit(dsn)
    allowed_query_keys = {
        "application_name",
        "channel_binding",
        "connect_timeout",
        "gssencmode",
        "keepalives",
        "keepalives_count",
        "keepalives_idle",
        "keepalives_interval",
        "options",
        "sslcert",
        "sslcompression",
        "sslcrl",
        "sslkey",
        "sslmode",
        "target_session_attrs",
    }
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key in allowed_query_keys
        ],
        doseq=True,
    )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))


def main() -> None:
    load_dotenv(".env.local")
    dsn = os.environ.get("POSTGRES_URL") or os.environ.get("POSTGRES_PRISMA_URL")
    if not dsn:
        raise SystemExit("Set POSTGRES_URL or POSTGRES_PRISMA_URL before running this script.")

    schema_path = Path(__file__).with_name("schema_postgres.sql")
    sql = schema_path.read_text(encoding="utf-8")

    with psycopg.connect(sanitize_postgres_dsn(dsn), prepare_threshold=None) as connection:
        connection.execute(sql)
        connection.commit()

    print(f"Applied {schema_path.name} to the configured Postgres database.")


if __name__ == "__main__":
    main()
