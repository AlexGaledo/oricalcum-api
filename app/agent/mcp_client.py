"""Load the workspace MCP tools into LangChain for a single chat request.

Each request gets its own MultiServerMCPClient configured with the caller's JWT
and project id in the request headers. The in-process FastMCP server reads those
headers (see app/mcp/context.py) to scope every tool call — the LLM only ever
supplies domain arguments, never identity.
"""

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import get_settings


async def load_workspace_tools(jwt: str, project_id: str) -> list[BaseTool]:
    settings = get_settings()
    client = MultiServerMCPClient(
        {
            "oricalcum": {
                "url": settings.resolved_mcp_url,
                "transport": "streamable_http",
                "headers": {
                    "Authorization": f"Bearer {jwt}",
                    "X-Project-Id": project_id,
                },
            }
        }
    )
    return await client.get_tools()
