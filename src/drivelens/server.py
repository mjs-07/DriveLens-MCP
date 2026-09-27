from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DriveLens")


@mcp.tool()
def ping() -> str:
    """Check whether the DriveLens MCP server is running."""
    return "DriveLens MCP is alive."


if __name__ == "__main__":
    mcp.run()