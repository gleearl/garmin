"""Print the current Garmin token store as a base64-encoded gzipped tar.

Run once locally after a successful login to generate the value for the
GARMIN_TOKEN_BASE64 GitHub secret:

    uv run python -m garmin_dash.token_dump
"""

from __future__ import annotations

import base64
import io
import tarfile
from pathlib import Path

from .client import TOKENSTORE


def main() -> None:
    p = Path(TOKENSTORE)
    if not p.exists():
        raise SystemExit(
            f"Token store not found at {TOKENSTORE}. "
            "Run `uv run python -m garmin_dash.login` first."
        )
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(p, arcname=".")
    encoded = base64.b64encode(buf.getvalue()).decode()
    print(encoded)


if __name__ == "__main__":
    main()
