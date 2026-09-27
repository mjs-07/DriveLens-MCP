from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from drivelens.auth.oauth import get_credentials
from drivelens.services.errors import (
    DriveAPIError,
    DriveAuthenticationError,
)


def get_drive_service() -> Resource:
    """
    Create an authenticated Google Drive API service.
    """
    try:
        credentials = get_credentials()

        return build(
            "drive",
            "v3",
            credentials=credentials,
        )

    except HttpError as exc:
        raise DriveAPIError(
            f"Google Drive API error: {exc}"
        ) from exc

    except Exception as exc:
        raise DriveAuthenticationError(
            f"Unable to authenticate with Google Drive: {exc}"
        ) from exc


def search_files(
    query: str,
    page_size: int = 20,
) -> list[dict]:
    """
    Search Google Drive files by name.

    Args:
        query: Text to search for in file names.
        page_size: Maximum number of results.

    Returns:
        A list of file metadata dictionaries.
    """

    if not query.strip():
        return []

    # Escape characters that have special meaning in Drive queries.
    safe_query = query.replace("\\", "\\\\").replace("'", "\\'")

    page_size = max(1, min(page_size, 100))

    drive = get_drive_service()

    response = _execute(
        drive.files()
        .list(
            q=f"name contains '{safe_query}' and trashed = false",
            pageSize=page_size,
            fields=(
                "files("
                "id,"
                "name,"
                "mimeType,"
                "size,"
                "createdTime,"
                "modifiedTime,"
                "webViewLink"
                ")"
            ),
            orderBy="modifiedTime desc",
        )
    )

    return response.get("files", [])

def get_file_info(file_id: str) -> dict:
    """
    Get metadata for a specific Google Drive file.

    Args:
        file_id: Google Drive file ID.

    Returns:
        File metadata dictionary.
    """

    if not file_id.strip():
        raise ValueError("file_id cannot be empty.")

    drive = get_drive_service()

    return _execute(
        drive.files()
        .get(
            fileId=file_id,
            fields=(
                "id,"
                "name,"
                "mimeType,"
                "size,"
                "createdTime,"
                "modifiedTime,"
                "webViewLink,"
                "parents,"
                "description"
            ),
        )
    )

def list_recent_files(limit: int = 20) -> list[dict]:
    """
    List recently modified Google Drive files.

    Args:
        limit: Maximum number of files to return.

    Returns:
        A list of recently modified file metadata.
    """

    limit = max(1, min(limit, 100))

    drive = get_drive_service()

    response = _execute(
        drive.files()
        .list(
            q="trashed = false",
            pageSize=limit,
            fields=(
                "files("
                "id,"
                "name,"
                "mimeType,"
                "size,"
                "createdTime,"
                "modifiedTime,"
                "webViewLink"
                ")"
            ),
            orderBy="modifiedTime desc",
        )
    )

    return response.get("files", [])

def find_large_files(
    minimum_size_mb: float = 10,
    limit: int = 20,
) -> list[dict]:
    """
    Find non-deleted Drive files whose reported size
    is at least the requested number of megabytes.

    Google Workspace-native files such as Docs and Sheets
    may not have a reported size, so those files are skipped.
    """

    minimum_size_mb = max(0, minimum_size_mb)
    limit = max(1, min(limit, 100))

    minimum_bytes = int(minimum_size_mb * 1024 * 1024)

    drive = get_drive_service()

    results = []
    page_token = None

    while True:
        response = _execute(
            drive.files()
            .list(
                q="trashed = false",
                pageSize=100,
                pageToken=page_token,
                fields=(
                    "nextPageToken,"
                    "files("
                    "id,"
                    "name,"
                    "mimeType,"
                    "size,"
                    "createdTime,"
                    "modifiedTime,"
                    "webViewLink"
                    ")"
                ),
            )
        )

        for file in response.get("files", []):
            size = file.get("size")

            if size is None:
                continue

            if int(size) >= minimum_bytes:
                results.append(file)

        page_token = response.get("nextPageToken")

        if not page_token:
            break

    # Largest files first.
    results.sort(
        key=lambda file: int(file.get("size", 0)),
        reverse=True,
    )

    return results[:limit]

def summarize_drive() -> dict:
    """
    Generate a metadata-only summary of the user's Google Drive.

    The summary includes:
    - total number of non-trashed files
    - number of files with reported sizes
    - total storage used by files with reported sizes
    - file count grouped by MIME type
    - largest files
    """

    drive = get_drive_service()

    total_files = 0
    files_with_size = 0
    total_storage_bytes = 0
    mime_type_counts = {}
    all_sized_files = []

    page_token = None

    while True:
        response = _execute(
            drive.files()
            .list(
                q="trashed = false",
                pageSize=100,
                pageToken=page_token,
                fields=(
                    "nextPageToken,"
                    "files("
                    "id,"
                    "name,"
                    "mimeType,"
                    "size,"
                    "createdTime,"
                    "modifiedTime,"
                    "webViewLink"
                    ")"
                ),
            )
        )

        files = response.get("files", [])

        for file in files:
            total_files += 1

            mime_type = file.get("mimeType", "unknown")
            mime_type_counts[mime_type] = (
                mime_type_counts.get(mime_type, 0) + 1
            )

            size = file.get("size")

            if size is not None:
                size_bytes = int(size)

                files_with_size += 1
                total_storage_bytes += size_bytes

                all_sized_files.append(file)

        page_token = response.get("nextPageToken")

        if not page_token:
            break

    all_sized_files.sort(
        key=lambda file: int(file.get("size", 0)),
        reverse=True,
    )

    largest_files = all_sized_files[:10]

    return {
        "total_files": total_files,
        "files_with_size": files_with_size,
        "total_storage_bytes": total_storage_bytes,
        "total_storage_mb": round(
            total_storage_bytes / (1024 * 1024),
            2,
        ),
        "total_storage_gb": round(
            total_storage_bytes / (1024 * 1024 * 1024),
            2,
        ),
        "mime_type_breakdown": mime_type_counts,
        "largest_files": largest_files,
    }

def _execute(request):
    """
    Execute a Google Drive API request and convert Google API
    errors into DriveServiceError exceptions.
    """
    try:
        return request.execute()

    except HttpError as exc:
        raise DriveAPIError(
            f"Google Drive API request failed: {exc}"
        ) from exc