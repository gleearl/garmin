"""Garmin Connect client wrapper with token persistence.

Authentication strategy (matches the upstream library's recommended flow):

1. Try to resume a session from the persisted token store (``~/.garminconnect``).
2. If that fails (missing/expired tokens), fall back to a full credential login,
   prompting for an MFA code if Garmin requires one, then persist the new tokens.

Credentials are only ever read at the interactive prompt or from a gitignored
``.env`` file -- they are never stored by this app.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
)

load_dotenv()

# Directory where garth/garminconnect persists OAuth tokens.
TOKENSTORE = os.path.expanduser(
    os.getenv("GARMINTOKENS", "~/.garminconnect")
)


def _restore_tokens_from_env() -> None:
    """Materialize the token store from GARMIN_TOKEN_BASE64 (for CI/GitHub Actions).

    The value is produced by `python -m garmin_dash.token_dump` — a base64-encoded
    gzipped tar of the token directory. A no-op if the env var is absent.
    """
    b64 = os.getenv("GARMIN_TOKEN_BASE64")
    if not b64:
        return
    import base64
    import io
    import tarfile
    from pathlib import Path

    data = base64.b64decode(b64)
    Path(TOKENSTORE).mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        tar.extractall(TOKENSTORE)


def _prompt_mfa() -> str:
    """Interactive MFA callback used during a fresh credential login."""
    return input("Garmin MFA one-time code: ").strip()


def resume() -> Garmin:
    """Resume an existing session from the token store.

    Checks GARMIN_TOKEN_BASE64 first so CI environments (GitHub Actions) can
    authenticate without an interactive login step.
    Raises if no valid tokens are present -- callers that need a guaranteed
    client (the API server) should surface a clear "run login first" message.
    """
    _restore_tokens_from_env()
    garmin = Garmin()
    garmin.login(TOKENSTORE)
    return garmin


def login_interactive() -> Garmin:
    """Full login flow. Resumes if possible, otherwise authenticates with
    credentials (prompting for email/password/MFA as needed) and persists tokens.
    """
    try:
        garmin = resume()
        print(f"Resumed Garmin session from {TOKENSTORE}")
        return garmin
    except (FileNotFoundError, GarminConnectAuthenticationError, Exception) as err:
        print(f"No usable saved session ({type(err).__name__}); logging in...")

    email = os.getenv("GARMIN_EMAIL") or input("Garmin email: ").strip()
    password = os.getenv("GARMIN_PASSWORD")
    if not password:
        import getpass

        password = getpass.getpass("Garmin password: ")

    Path(TOKENSTORE).mkdir(parents=True, exist_ok=True)
    garmin = Garmin(email=email, password=password, prompt_mfa=_prompt_mfa)
    # garminconnect 0.3.x persists tokens when a tokenstore path is passed to login()
    # (see garminconnect/__init__.py -> self.client.dump(tokenstore_path)). The old
    # 0.2.x `garmin.garth.dump(...)` no longer exists.
    garmin.login(TOKENSTORE)
    print(f"Login successful; tokens saved to {TOKENSTORE}")
    return garmin


def get_client() -> Garmin:
    """Return a ready-to-use client for non-interactive callers (sync/API).

    Only resumes from saved tokens -- it will not block on prompts. If no
    tokens exist, raises a clear error telling the user to run the login step.
    """
    try:
        return resume()
    except Exception as err:  # noqa: BLE001 - surface a friendly message
        raise RuntimeError(
            "Not logged in to Garmin. Run `uv run python -m garmin_dash.login` "
            f"first to create a session in {TOKENSTORE}. (cause: {err})"
        ) from err
