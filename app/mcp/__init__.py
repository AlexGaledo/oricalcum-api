"""Oricalcum MCP server package.

Importing this package builds the assembled FastMCP server `mcp` with all tools
registered. Tool modules are imported for their side effect of decorating
functions with `@mcp.tool`.
"""

from app.mcp.oricalcum_mcp import mcp

# Side-effect imports: register tools onto the shared `mcp` instance.
from app.mcp import nodes_mcp  # noqa: E402, F401
from app.mcp import edges_mcp  # noqa: E402, F401
from app.mcp import calendar_mcp  # noqa: E402, F401

__all__ = ["mcp"]
