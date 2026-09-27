import json

from drivelens.services.drive import (
    summarize_drive as summarize_drive_service,
    find_large_files,
    get_file_info,
    list_recent_files,
    search_files,
)


def register_drive_tools(mcp):
    """
    Register Google Drive tools with the MCP server.
    """

    @mcp.tool()
    def search_drive(query: str, limit: int = 20) -> str:
        """
        Search Google Drive files by name.

        Args:
            query: Text to search for in file names.
            limit: Maximum number of matching files.
        """

        files = search_files(
            query=query,
            page_size=limit,
        )

        return json.dumps(
            {
                "query": query,
                "count": len(files),
                "files": files,
            },
            indent=2,
        )

    @mcp.tool()
    def get_drive_file_info(file_id: str) -> str:
        """
        Get metadata about a specific Google Drive file.

        Args:
            file_id: Google Drive file ID.
        """

        file = get_file_info(file_id)

        return json.dumps(
            file,
            indent=2,
        )

    @mcp.tool()
    def list_recent_drive_files(limit: int = 20) -> str:
        """
        List recently modified Google Drive files.

        Args:
            limit: Maximum number of files to return.
        """

        files = list_recent_files(limit)

        return json.dumps(
            {
                "count": len(files),
                "files": files,
            },
            indent=2,
        )

    @mcp.tool()
    def find_large_drive_files(
        minimum_size_mb: float = 10,
        limit: int = 20,
    ) -> str:
        """
        Find large Google Drive files.

        Args:
            minimum_size_mb: Minimum reported file size in MB.
            limit: Maximum number of files to return.
        """

        files = find_large_files(
            minimum_size_mb=minimum_size_mb,
            limit=limit,
        )

        return json.dumps(
            {
                "minimum_size_mb": minimum_size_mb,
                "count": len(files),
                "files": files,
            },
            indent=2,
        )

    @mcp.tool()
    def summarize_drive() -> str:
        """
        Summarize the user's Google Drive using metadata.
        """
        summary = summarize_drive_service()

        return json.dumps(
            summary,
            indent=2,
        )