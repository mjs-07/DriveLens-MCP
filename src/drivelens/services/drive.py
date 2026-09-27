from googleapiclient.discovery import Resource, build

from src.drivelens.auth.oauth import get_credentials


def get_drive_service() -> Resource:
    """
    Create an authenticated Google Drive API service.
    """
    credentials = get_credentials()

    return build(
        "drive",
        "v3",
        credentials=credentials,
    )