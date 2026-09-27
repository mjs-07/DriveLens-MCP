import drivelens.services.drive as drive_service


def test_get_drive_service(monkeypatch):
    fake_credentials = object()
    fake_drive_service = object()

    monkeypatch.setattr(
        drive_service,
        "get_credentials",
        lambda: fake_credentials,
    )

    def fake_build(service_name, version, credentials):
        assert service_name == "drive"
        assert version == "v3"
        assert credentials is fake_credentials

        return fake_drive_service

    monkeypatch.setattr(
        drive_service,
        "build",
        fake_build,
    )

    result = drive_service.get_drive_service()

    assert result is fake_drive_service