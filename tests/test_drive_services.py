import drivelens.services.drive as drive_service


class FakeRequest:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class FakeFilesResource:
    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def get(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeRequest(self.response)

    def list(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeRequest(self.response)


class FakeDrive:
    def __init__(self, response):
        self.files_resource = FakeFilesResource(response)

    def files(self):
        return self.files_resource


def test_get_file_info(monkeypatch):
    expected = {
        "id": "123",
        "name": "test.pdf",
        "mimeType": "application/pdf",
        "size": "1024",
    }

    fake_drive = FakeDrive(expected)

    monkeypatch.setattr(
        drive_service,
        "get_drive_service",
        lambda: fake_drive,
    )

    result = drive_service.get_file_info("123")

    assert result == expected
    assert fake_drive.files_resource.last_kwargs["fileId"] == "123"


def test_list_recent_files(monkeypatch):
    expected = [
        {
            "id": "1",
            "name": "recent.pdf",
            "mimeType": "application/pdf",
        },
        {
            "id": "2",
            "name": "recent.txt",
            "mimeType": "text/plain",
        },
    ]

    fake_drive = FakeDrive({"files": expected})

    monkeypatch.setattr(
        drive_service,
        "get_drive_service",
        lambda: fake_drive,
    )

    result = drive_service.list_recent_files(10)

    assert result == expected
    assert fake_drive.files_resource.last_kwargs["pageSize"] == 10
    assert fake_drive.files_resource.last_kwargs["orderBy"] == "modifiedTime desc"


def test_find_large_files(monkeypatch):
    expected = [
        {
            "id": "1",
            "name": "large.bin",
            "mimeType": "application/octet-stream",
            "size": "10485760",
        },
        {
            "id": "2",
            "name": "small.txt",
            "mimeType": "text/plain",
            "size": "1024",
        },
    ]

    fake_drive = FakeDrive({"files": expected})

    monkeypatch.setattr(
        drive_service,
        "get_drive_service",
        lambda: fake_drive,
    )

    result = drive_service.find_large_files(
        minimum_size_mb=5,
        limit=10,
    )

    assert len(result) == 1
    assert result[0]["name"] == "large.bin"
    assert result[0]["size"] == "10485760"


def test_summarize_drive(monkeypatch):
    files = [
        {
            "id": "1",
            "name": "large.bin",
            "mimeType": "application/octet-stream",
            "size": "10485760",
        },
        {
            "id": "2",
            "name": "photo.jpg",
            "mimeType": "image/jpeg",
            "size": "5242880",
        },
        {
            "id": "3",
            "name": "notes.txt",
            "mimeType": "text/plain",
        },
    ]

    fake_drive = FakeDrive({"files": files})

    monkeypatch.setattr(
        drive_service,
        "get_drive_service",
        lambda: fake_drive,
    )

    result = drive_service.summarize_drive()

    assert result["total_files"] == 3
    assert result["files_with_size"] == 2
    assert result["total_storage_bytes"] == 15728640
    assert result["total_storage_mb"] == 15.0
    assert result["total_storage_gb"] == 0.01

    assert result["mime_type_breakdown"]["application/octet-stream"] == 1
    assert result["mime_type_breakdown"]["image/jpeg"] == 1
    assert result["mime_type_breakdown"]["text/plain"] == 1

    assert result["largest_files"][0]["name"] == "large.bin"