import os

from pydantic import AnyHttpUrl

from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
    RevocationOptions,
)
from mcp.server.fastmcp import FastMCP
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from drivelens.auth.mcp_oauth import DriveLensOAuthProvider
from drivelens.tools.drive_tools import register_drive_tools


HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8000"))

SERVER_URL = os.getenv(
    "SERVER_URL",
    f"http://localhost:{PORT}",
)

MCP_RESOURCE_URL = f"{SERVER_URL}/mcp"


oauth_provider = DriveLensOAuthProvider(
    login_url=f"{SERVER_URL}/login",
    server_url=SERVER_URL,
)


mcp = FastMCP(
    "DriveLens",

    host=HOST,
    port=PORT,

    auth_server_provider=oauth_provider,

    auth=AuthSettings(
        issuer_url=AnyHttpUrl(SERVER_URL),

        resource_server_url=AnyHttpUrl(
            MCP_RESOURCE_URL
        ),

        required_scopes=[
            "drive:read"
        ],

        validate_token_resource=True,

        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=[
                "drive:read"
            ],
            default_scopes=[
                "drive:read"
            ],
        ),

        revocation_options=RevocationOptions(
            enabled=True,
        ),
    ),
)


@mcp.custom_route(
    "/login",
    methods=["GET"],
)
async def login_page(
    request: Request,
) -> Response:

    state = request.query_params.get("state")

    if not state:
        raise HTTPException(
            400,
            "Missing state parameter",
        )

    return await oauth_provider.get_login_page(
        state
    )


@mcp.custom_route(
    "/login/callback",
    methods=["POST"],
)
async def login_callback(
    request: Request,
) -> Response:

    return await oauth_provider.handle_login_callback(
        request
    )


@mcp.tool()
def ping() -> str:
    """Check whether the DriveLens MCP server is running."""
    return "DriveLens MCP is alive."


register_drive_tools(mcp)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
    )