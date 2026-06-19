"""One-time interactive login to establish a Garmin session.

Run once:  uv run python -m garmin_dash.login

Handles MFA and persists OAuth tokens to the token store so that the sync job
and API server can run non-interactively afterwards.
"""

from __future__ import annotations

from .client import login_interactive


def main() -> None:
    client = login_interactive()
    # Touch a lightweight endpoint to confirm the session actually works.
    name = client.get_full_name()
    print(f"Logged in as: {name}")


if __name__ == "__main__":
    main()
