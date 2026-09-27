class DriveServiceError(Exception):
    """Base exception for Drive service errors."""


class DriveAuthenticationError(DriveServiceError):
    """Raised when Google authentication fails."""


class DriveAPIError(DriveServiceError):
    """Raised when the Google Drive API returns an error."""