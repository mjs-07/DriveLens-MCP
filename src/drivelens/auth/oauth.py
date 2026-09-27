from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


# Project root:
# DriveLens-MCP/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly"
]


def get_credentials() -> Credentials:
    """
    Get valid Google OAuth credentials for DriveLens.

    On the first run, this opens a browser and asks the user
    to authorize read-only Google Drive metadata access.

    On subsequent runs, credentials are loaded from token.json
    and refreshed automatically when necessary.
    """

    credentials = None

    # Reuse previously saved credentials.
    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES,
        )

    # No valid credentials yet.
    if not credentials or not credentials.valid:

        # Refresh an expired access token if possible.
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        # Otherwise start the browser-based OAuth flow.
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"Google OAuth credentials not found: {CREDENTIALS_FILE}"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                SCOPES,
            )

            credentials = flow.run_local_server(port=0)

        # Save credentials for future runs.
        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    return credentials