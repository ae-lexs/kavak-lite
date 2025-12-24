from __future__ import annotations

import os


def database_url() -> str:
    url = os.getenv("DATABASE_URL")

    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    return url
