from types import SimpleNamespace

import drivelens.auth.oauth as oauth


def test_get_credentials_uses_existing_token(monkeypatch, tmp_path):
    token_file = tmp_path / "token.json"
    token_file.write_text("{}", encoding="utf-8")

    fake_credentials = SimpleNamespace(
        valid=True,
        expired=False,
        refresh_token=None,
        scopes=["https://www.googleapis.com/auth/drive.metadata.readonly"],
        to_json=lambda: "{}",
    )

    monkeypatch.setattr(oauth, "TOKEN_FILE", token_file)
    monkeypatch.setattr(
        oauth.Credentials,
        "from_authorized_user_file",
        lambda *_args: fake_credentials,
    )

    credentials = oauth.get_credentials()

    assert credentials.valid is True
    assert credentials.expired is False
    assert (
        "https://www.googleapis.com/auth/drive.metadata.readonly"
        in credentials.scopes
    )