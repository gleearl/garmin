"""Garmin Connect client wrapper with token persistence.

Authentication strategy (matches the upstream library's recommended flow):

1. Try to resume a session from the persisted token store (``~/.garminconnect``).
2. If that fails (missing/expired tokens), fall back to a full credential login,
   prompting for an MFA code if Garmin requires one, then persist the new tokens.

Credentials are only ever read at the interactive prompt or from a gitignored
``.env`` file -- they are never stored by this app.

Garmin rotates the refresh token on every refresh, so the token store is
mutable state, not a fixed credential. Whatever is already on disk wins over
``GARMIN_TOKEN_BASE64``; the env var is only a bootstrap for a machine that has
no store yet. A CI job that restores the store from the env var on every run
replays a refresh token that Garmin has already rotated away, which works until
the original expires and then fails with ``invalid_grant``. See sync.yml, which
round-trips the store through IONOS so each run persists the rotated token.
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
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


# The single file garminconnect reads and rewrites inside TOKENSTORE.
TOKEN_FILE = Path(TOKENSTORE) / "garmin_tokens.json"

# Written only after Garmin actually accepts the tokens. A sibling of the store
# rather than a file inside it, so `token_dump` (which tars the whole directory)
# can't bake a stale marker into the secret. CI keys its "should I persist this
# token store?" decision off this file -- see sync.yml.
AUTH_OK_MARKER = Path(str(TOKENSTORE) + ".auth-ok")


def _env_token_bytes() -> bytes | None:
    """The garmin_tokens.json carried by GARMIN_TOKEN_BASE64, if it is set."""
    b64 = os.getenv("GARMIN_TOKEN_BASE64")
    if not b64:
        return None
    import base64
    import io
    import tarfile

    with contextlib.suppress(Exception):
        with tarfile.open(fileobj=io.BytesIO(base64.b64decode(b64)), mode="r:gz") as tar:
            member = tar.extractfile("./garmin_tokens.json") or tar.extractfile(
                "garmin_tokens.json"
            )
            if member:
                return member.read()
    return None


def _write_token_store(payload: bytes) -> None:
    """Install a token store, owner-only, matching garminconnect's own perms."""
    Path(TOKENSTORE).mkdir(mode=0o700, parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        Path(TOKENSTORE).chmod(0o700)
    TOKEN_FILE.write_bytes(payload)
    with contextlib.suppress(OSError):
        TOKEN_FILE.chmod(0o600)


def _restore_tokens_from_env() -> None:
    """Seed the token store from GARMIN_TOKEN_BASE64 (for CI/GitHub Actions).

    The value is produced by `python -m garmin_dash.token_dump` — a base64-encoded
    gzipped tar of the token directory. A no-op if the env var is absent.

    An existing store always wins: the env var is a fixed snapshot, while the
    on-disk store carries the rotated refresh token from the last run. Restoring
    over a live store would roll the credential backwards to a token Garmin has
    already invalidated. See `_reseed_from_env` for the recovery path when the
    existing store turns out to be the dead one.
    """
    payload = _env_token_bytes()
    if payload is None:
        return
    if TOKEN_FILE.exists():
        print(f"Using existing token store at {TOKENSTORE} (ignoring GARMIN_TOKEN_BASE64)")
        return
    _write_token_store(payload)
    print(f"Seeded token store at {TOKENSTORE} from GARMIN_TOKEN_BASE64")


def _reseed_from_env() -> bool:
    """Replace a rejected token store with the GARMIN_TOKEN_BASE64 snapshot.

    Without this, a dead token that reached the shared store (IONOS) would
    shadow the env var forever: the store exists, so the snapshot is ignored,
    so refreshing the secret has no effect. Falling back keeps "refresh the
    secret" working as the documented recovery lever.
    """
    payload = _env_token_bytes()
    if payload is None:
        return False
    with contextlib.suppress(OSError):
        if TOKEN_FILE.read_bytes() == payload:
            return False  # Same token; retrying would fail identically.
    _write_token_store(payload)
    print("Saved tokens were rejected; retrying with GARMIN_TOKEN_BASE64.")
    return True


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
    # Clear first: the marker must describe this attempt, never a previous one.
    with contextlib.suppress(OSError):
        AUTH_OK_MARKER.unlink()
    garmin = Garmin()
    garmin.login(TOKENSTORE)
    # login() round-trips a real API call, so reaching here means Garmin accepted
    # the tokens now on disk -- the only state that is safe to share with the
    # next run.
    with contextlib.suppress(OSError):
        AUTH_OK_MARKER.write_text("ok\n")
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


# Garmin echoes the rejected token back in its error body, so anything captured
# from the logger has to be scrubbed before it reaches a log or a raised message.
# Long *and* containing a digit: matches base64/JWT blobs while leaving prose
# and identifiers like GarminConnectAuthenticationError intact.
_TOKENISH = re.compile(r"(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{32,}")


def _redact(text: str, limit: int = 200) -> str:
    """Strip token-shaped blobs and cap length for safe display in CI logs."""
    cleaned = _TOKENISH.sub("<redacted>", text)
    return cleaned if len(cleaned) <= limit else cleaned[:limit] + "..."


class _RefreshErrorCapture(logging.Handler):
    """Collect the refresh failure garminconnect only logs at DEBUG.

    ``Client._refresh_session`` swallows a failed token refresh and retries the
    request with the stale bearer token, so the caller sees a bare ``API Error
    401`` with no body. The real reason (e.g. ``invalid_grant``) is only ever
    logged. Capturing it turns an opaque 401 into an actionable message.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        with contextlib.suppress(Exception):
            msg = record.getMessage()
            if "refresh" in msg.lower():
                self.messages.append(_redact(msg))


@contextlib.contextmanager
def _capture_refresh_errors():
    """Temporarily tap garminconnect's logger without changing global config."""
    logger = logging.getLogger("garminconnect")
    handler = _RefreshErrorCapture()
    previous_level, previous_propagate = logger.level, logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    # Keep the debug chatter out of the app's own logging output.
    logger.propagate = False
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate


def get_client() -> Garmin:
    """Return a ready-to-use client for non-interactive callers (sync/API).

    Only resumes from saved tokens -- it will not block on prompts. Raises a
    message that distinguishes "never logged in" from "the saved tokens were
    rejected", since the two need different fixes.
    """
    try:
        with _capture_refresh_errors() as captured:
            return resume()
    except Exception as err:  # noqa: BLE001 - surface a friendly message
        # A rejected store is recoverable if the env var holds a different
        # snapshot -- typically a freshly refreshed secret after the shared
        # store went stale.
        if TOKEN_FILE.exists() and _reseed_from_env():
            try:
                with _capture_refresh_errors() as captured:
                    return resume()
            except Exception as retry_err:  # noqa: BLE001
                err = retry_err

        if not TOKEN_FILE.exists():
            raise RuntimeError(
                "Not logged in to Garmin. Run `uv run python -m garmin_dash.login` "
                f"first to create a session in {TOKENSTORE}. (cause: {err})"
            ) from err

        detail = captured.messages[-1] if captured.messages else _redact(str(err))
        raise RuntimeError(
            f"Garmin rejected the saved tokens in {TOKENSTORE}. The refresh token "
            "has expired or was rotated away (Garmin issues a new one on every "
            "refresh, so a stale copy stops working). Re-run "
            "`uv run python -m garmin_dash.login`, then refresh the "
            "GARMIN_TOKEN_BASE64 secret with `python -m garmin_dash.token_dump`. "
            f"(cause: {detail})"
        ) from err
