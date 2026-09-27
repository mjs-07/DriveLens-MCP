import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


PROJECT_ROOT = Path(__file__).resolve().parents[3]

CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly"
]


def _load_credentials_from_environment() -> Credentials | None:
    """Load Google OAuth credentials from GOOGLE_TOKEN_JSON."""

    token_json = os.getenv("GOOGLE_TOKEN_JSON")

    if not token_json:
        return None

    try:
        token_data = json.loads(token_json)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "GOOGLE_TOKEN_JSON contains invalid JSON"
        ) from exc

    return Credentials.from_authorized_user_info(
        token_data,
        SCOPES,
    )


def get_credentials() -> Credentials:
    """
    Get valid Google OAuth credentials for DriveLens.

    Local development:
        Uses token.json and credentials.json.

    Deployment:
        Uses GOOGLE_TOKEN_JSON environment variable.
    """

    credentials = None

    # ---------------------------------------------------------
    # 1. Deployment credentials
    # ---------------------------------------------------------
    if os.getenv("GOOGLE_TOKEN_JSON"):
        credentials = _load_credentials_from_environment()

    # ---------------------------------------------------------
    # 2. Local saved credentials
    # ---------------------------------------------------------
    elif TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES,
        )

    # ---------------------------------------------------------
    # 3. Refresh expired credentials
    # ---------------------------------------------------------
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    # ---------------------------------------------------------
    # 4. Local interactive OAuth
    # ---------------------------------------------------------
    elif not credentials or not credentials.valid:

        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"Google OAuth credentials not found: {CREDENTIALS_FILE}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES,
        )

        credentials = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    return credentials