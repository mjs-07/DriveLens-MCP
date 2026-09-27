import pytest
from googleapiclient.errors import HttpError
from google.auth.exceptions import GoogleAuthError

import drivelens.services.drive as drive_service
from drivelens.services.errors import (
    DriveAPIError,
    DriveAuthenticationError,
)


def test_execute_converts_http_error_to_drive_api_error():
    class FakeRequest:
        def execute(self):
            raise HttpError(
                resp=type(
                    "Response",
                    (),
                    {
                        "status": 403,
                        "reason": "Forbidden",
                    },
                )(),
                content=b'{"error": {"message": "Access denied"}}',
            )

    with pytest.raises(DriveAPIError) as exc_info:
        drive_service._execute(FakeRequest())

    assert "Google Drive API request failed" in str(exc_info.value)


def test_get_drive_service_converts_authentication_error(monkeypatch):
    def fake_get_credentials():
        raise GoogleAuthError("Authentication failed")

    monkeypatch.setattr(
        drive_service,
        "get_credentials",
        fake_get_credentials,
    )

    with pytest.raises(DriveAuthenticationError) as exc_info:
        drive_service.get_drive_service()

    assert "Unable to authenticate with Google Drive" in str(
        exc_info.value
    )