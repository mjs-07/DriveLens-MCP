import secrets
import time
from typing import Any

from pydantic import AnyHttpUrl

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthToken,
)


class DriveLensOAuthProvider(
    OAuthAuthorizationServerProvider[
        AuthorizationCode,
        RefreshToken,
        AccessToken,
    ]
):
    """
    Minimal OAuth 2.1 authorization provider for DriveLens MVP.

    This provider is intended for local development/MVP use.
    Production deployment should use a proper external identity provider.
    """

    def __init__(
        self,
        login_url: str,
        server_url: str,
        username: str = "demo_user",
        password: str = "demo_password",
        scope: str = "drive:read",
    ):
        self.login_url = login_url
        self.server_url = server_url

        self.username = username
        self.password = password
        self.scope = scope

        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.tokens: dict[str, AccessToken] = {}

        self.state_mapping: dict[str, dict[str, Any]] = {}

    async def get_client(
        self,
        client_id: str,
    ) -> OAuthClientInformationFull | None:
        return self.clients.get(client_id)

    async def register_client(
        self,
        client_info: OAuthClientInformationFull,
    ):
        if not client_info.client_id:
            raise ValueError("No client_id provided")

        self.clients[client_info.client_id] = client_info

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        """
        Begin OAuth authorization-code flow.

        PKCE parameters are supplied by the MCP SDK/client.
        """

        state = params.state or secrets.token_hex(16)

        self.state_mapping[state] = {
            "redirect_uri": str(params.redirect_uri),
            "code_challenge": params.code_challenge,
            "redirect_uri_provided_explicitly": (
                params.redirect_uri_provided_explicitly
            ),
            "client_id": client.client_id,
            "resource": params.resource,
        }

        return (
            f"{self.login_url}"
            f"?state={state}"
            f"&client_id={client.client_id}"
        )

    async def get_login_page(
        self,
        state: str,
    ) -> HTMLResponse:
        if not state:
            raise HTTPException(
                400,
                "Missing state parameter",
            )

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DriveLens Authentication</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 420px;
                    margin: 80px auto;
                    padding: 24px;
                }}

                input {{
                    width: 100%;
                    padding: 10px;
                    margin: 8px 0 16px;
                    box-sizing: border-box;
                }}

                button {{
                    width: 100%;
                    padding: 10px;
                    background: #333;
                    color: white;
                    border: none;
                    cursor: pointer;
                }}
            </style>
        </head>

        <body>
            <h2>DriveLens Authentication</h2>

            <p>
                Sign in to authorize this MCP client.
            </p>

            <form
                action="{self.server_url.rstrip('/')}/login/callback"
                method="post"
            >
                <input
                    type="hidden"
                    name="state"
                    value="{state}"
                />

                <label>Username</label>
                <input
                    type="text"
                    name="username"
                    required
                />

                <label>Password</label>
                <input
                    type="password"
                    name="password"
                    required
                />

                <button type="submit">
                    Authorize DriveLens
                </button>
            </form>
        </body>
        </html>
        """

        return HTMLResponse(content=html)

    async def handle_login_callback(
        self,
        request: Request,
    ) -> Response:
        form = await request.form()

        username = form.get("username")
        password = form.get("password")
        state = form.get("state")

        if not username or not password or not state:
            raise HTTPException(
                400,
                "Missing username, password, or state",
            )

        if not isinstance(username, str):
            raise HTTPException(400, "Invalid username")

        if not isinstance(password, str):
            raise HTTPException(400, "Invalid password")

        if not isinstance(state, str):
            raise HTTPException(400, "Invalid state")

        redirect_uri = await self.authenticate(
            username,
            password,
            state,
        )

        return RedirectResponse(
            url=redirect_uri,
            status_code=302,
        )

    async def authenticate(
        self,
        username: str,
        password: str,
        state: str,
    ) -> str:
        state_data = self.state_mapping.get(state)

        if not state_data:
            raise HTTPException(
                400,
                "Invalid or expired OAuth state",
            )

        if (
            username != self.username
            or password != self.password
        ):
            raise HTTPException(
                401,
                "Invalid credentials",
            )

        redirect_uri = state_data["redirect_uri"]
        code_challenge = state_data["code_challenge"]
        client_id = state_data["client_id"]

        if not code_challenge:
            raise HTTPException(
                400,
                "PKCE code challenge is required",
            )

        code = f"dl_code_{secrets.token_hex(24)}"

        authorization_code = AuthorizationCode(
            code=code,
            client_id=client_id,
            redirect_uri=AnyHttpUrl(redirect_uri),
            redirect_uri_provided_explicitly=(
                state_data["redirect_uri_provided_explicitly"]
            ),
            expires_at=time.time() + 300,
            scopes=[self.scope],
            code_challenge=code_challenge,
            resource=state_data.get("resource"),
            subject=username,
        )

        self.auth_codes[code] = authorization_code

        del self.state_mapping[state]

        return construct_redirect_uri(
            redirect_uri,
            code=code,
            state=state,
        )

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:
        return self.auth_codes.get(authorization_code)

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:

        if authorization_code.code not in self.auth_codes:
            raise ValueError(
                "Invalid authorization code"
            )

        token = f"dl_token_{secrets.token_hex(32)}"

        self.tokens[token] = AccessToken(
            token=token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time()) + 3600,
            resource=authorization_code.resource,
            subject=authorization_code.subject,
        )

        del self.auth_codes[authorization_code.code]

        return OAuthToken(
            access_token=token,
            token_type="Bearer",
            expires_in=3600,
            scope=" ".join(
                authorization_code.scopes
            ),
        )

    async def load_access_token(
        self,
        token: str,
    ) -> AccessToken | None:

        access_token = self.tokens.get(token)

        if not access_token:
            return None

        if (
            access_token.expires_at
            and access_token.expires_at < time.time()
        ):
            del self.tokens[token]
            return None

        return access_token

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:
        return None

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        raise NotImplementedError(
            "Refresh tokens are not implemented in MVP v1."
        )

    async def revoke_token(
        self,
        token: str,
        token_type_hint: str | None = None,
    ) -> None:
        self.tokens.pop(token, None)