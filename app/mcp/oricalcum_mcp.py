"""Main MCP server for the Oricalcum in-workspace AI assistant.

A single FastMCP instance that all tool modules register onto. The agent layer
(`app/agent`) connects to this server over streamable-http and exposes the tools
to the Gemini model. Tool modules import `mcp` from here and decorate functions
with `@mcp.tool`; importing them (done in `app/mcp/__init__.py`) registers the
tools on this shared instance.

Scope (project + user) is never taken from LLM-supplied arguments — it is read
from the MCP request headers in `app/mcp/context.py`. See that module for the
security boundary.
"""

from fastmcp import FastMCP

mcp = FastMCP(
    name="oricalcum",
    instructions=(
        "Tools to read and edit the current Oricalcum workspace: its nodes "
        "(cards/tasks on the canvas) and calendar meetings. Every tool operates "
        "on the single workspace the user currently has open; you do not choose "
        "the workspace or the user."
    ),
)
