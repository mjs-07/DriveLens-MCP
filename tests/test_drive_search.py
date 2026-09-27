import drivelens.services.drive as drive_service


def test_search_files_empty_query(monkeypatch):
    def fail_if_called():
        raise AssertionError(
            "Google Drive should not be called for an empty query."
        )

    monkeypatch.setattr(
        drive_service,
        "get_drive_service",
        fail_if_called,
    )

    result = drive_service.search_files("   ")

    assert result == []


def test_search_files_returns_files(monkeypatch):
    expected_files = [
        {
            "id": "123",
            "name": "AI Project",
            "mimeType": "application/pdf",
        },
        {
            "id": "456",
            "name": "AI Notes",
            "mimeType": "text/plain",
        },
    ]

    class FakeRequest:
        def execute(self):
            return {"files": expected_files}

    class FakeFiles:
        def list(self, **kwargs):
            assert "q" in kwargs
            assert "AI" in kwargs["q"]
            assert kwargs["pageSize"] == 20

            return FakeRequest()

    class FakeDrive:
        def files(self):
            return FakeFiles()

    monkeypatch.setattr(
        drive_service,
        "get_drive_service",
        lambda: FakeDrive(),
    )

    result = drive_service.search_files("AI")

    assert result == expected_files