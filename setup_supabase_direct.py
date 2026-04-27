from __future__ import annotations

import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


def sanitize_postgres_dsn(dsn: str) -> str:
    parsed = urlsplit(dsn)
    allowed_query_keys = {"connect_timeout", "sslmode", "target_session_attrs", "application_name"}
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

    with psycopg.connect(
        sanitize_postgres_dsn(dsn),
        row_factory=dict_row,
        prepare_threshold=None,
    ) as connection:
        user_count = connection.execute('SELECT COUNT(*) AS count FROM "user"').fetchone()["count"]
        item_count = connection.execute("SELECT COUNT(*) AS count FROM item").fetchone()["count"]
        order_count = connection.execute("SELECT COUNT(*) AS count FROM orders").fetchone()["count"]

    print(f"user={user_count}, item={item_count}, orders={order_count}")


if __name__ == "__main__":
    main()
