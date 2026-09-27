import time
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.requests import Request

from drivelens.auth.mcp_oauth import DriveLensOAuthProvider
from mcp.shared.auth import OAuthClientInformationFull


@pytest.fixture
def provider():
    return DriveLensOAuthProvider(
        login_url="http://localhost:8000/login",
        server_url="http://localhost:8000",
    )


@pytest.fixture
def client():
    return OAuthClientInformationFull(
        client_id="test-client",
        redirect_uris=["http://localhost:9000/callback"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="none",
    )


@pytest.mark.anyio
async def test_register_and_get_client(provider, client):
    await provider.register_client(client)

    result = await provider.get_client("test-client")

    assert result is not None
    assert result.client_id == "test-client"


@pytest.mark.anyio
async def test_login_callback_redirect_includes_issuer(provider, client):
    provider.server_url = "https://drivelens-mcp.onrender.com"
    await provider.register_client(client)

    state = "test-state"
    provider.state_mapping[state] = {
        "redirect_uri": "http://localhost:9000/callback",
        "code_challenge": "test-challenge",
        "redirect_uri_provided_explicitly": True,
        "client_id": client.client_id,
        "resource": "http://localhost:8000/mcp",
    }
    body = b"username=demo_user&password=demo_password&state=test-state"

    async def receive():
        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "headers": [
                (b"content-type", b"application/x-www-form-urlencoded"),
            ],
            "path": "/login/callback",
            "query_string": b"",
        },
        receive,
    )

    response = await provider.handle_login_callback(request)

    assert response.status_code == 307
    location = urlsplit(response.headers["location"])
    query = parse_qs(location.query)
    assert f"{location.scheme}://{location.netloc}{location.path}" == (
        "http://localhost:9000/callback"
    )
    assert query["iss"] == ["https://drivelens-mcp.onrender.com/"]
    assert query["state"] == [state]
    assert len(query["code"]) == 1

    authorization_code = provider.auth_codes[query["code"][0]]
    assert authorization_code.client_id == client.client_id
    assert authorization_code.code_challenge == "test-challenge"
    assert authorization_code.scopes == ["drive:read"]
    assert authorization_code.resource == "http://localhost:8000/mcp"


@pytest.mark.anyio
async def test_exchange_authorization_code_creates_access_token(
    provider,
    client,
):
    await provider.register_client(client)

    from mcp.server.auth.provider import AuthorizationCode

    authorization_code = AuthorizationCode(
        code="test-code",
        client_id="test-client",
        redirect_uri="http://localhost:9000/callback",
        redirect_uri_provided_explicitly=True,
        expires_at=time.time() + 300,
        scopes=["drive:read"],
        code_challenge="test-challenge",
        resource="http://localhost:8000/mcp",
        subject="demo_user",
    )

    provider.auth_codes["test-code"] = authorization_code

    token_response = await provider.exchange_authorization_code(
        client,
        authorization_code,
    )

    assert token_response.access_token
    assert token_response.token_type == "Bearer"
    assert token_response.expires_in == 3600
    assert token_response.scope == "drive:read"

    access_token = await provider.load_access_token(
        token_response.access_token
    )

    assert access_token is not None
    assert access_token.client_id == "test-client"
    assert access_token.scopes == ["drive:read"]
    assert access_token.resource == "http://localhost:8000/mcp"
    assert access_token.subject == "demo_user"


@pytest.mark.anyio
async def test_expired_access_token_is_rejected(
    provider,
    client,
):
    from mcp.server.auth.provider import AccessToken

    expired_token = "expired-token"

    provider.tokens[expired_token] = AccessToken(
        token=expired_token,
        client_id="test-client",
        scopes=["drive:read"],
        expires_at=int(time.time()) - 1,
        resource="http://localhost:8000/mcp",
        subject="demo_user",
    )

    result = await provider.load_access_token(expired_token)

    assert result is None
    assert expired_token not in provider.tokens


@pytest.mark.anyio
async def test_unknown_access_token_is_rejected(provider):
    result = await provider.load_access_token("does-not-exist")

    assert result is None