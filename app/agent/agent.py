"""Build and stream the workspace ReAct agent.

The agent is a LangGraph ReAct agent (a LCEL Runnable) wrapping the Gemini model
and the per-request MCP tools. It is built fresh for each chat request because the
tools are bound to that request's auth/project scope.
"""

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from app.agent.llm import build_llm
from app.agent.mcp_client import load_workspace_tools
from app.agent.prompts import SYSTEM_PROMPT


def _to_messages(history: list[dict[str, str]], user_message: str) -> list[BaseMessage]:
    """Convert persisted {role, content} rows + the new user turn into messages."""
    messages: list[BaseMessage] = []
    for row in history:
        content = row["content"]
        if row["role"] == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    messages.append(HumanMessage(content=user_message))
    return messages


def _chunk_text(chunk: AIMessageChunk) -> str:
    """Extract plain text from a model chunk, ignoring tool-call/function parts."""
    content = chunk.content
    if isinstance(content, str):
        return content
    # Gemini can stream a list of content blocks; keep only text blocks.
    parts: list[str] = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


async def build_agent(jwt: str, project_id: str) -> Any:
    tools = await load_workspace_tools(jwt, project_id)
    llm = build_llm()
    # Inject current time so the agent can resolve relative dates ("tomorrow 3pm")
    # into absolute unix-ms timestamps for create_meeting.
    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    prompt = (
        f"{SYSTEM_PROMPT}\n\nCurrent server time: {now.isoformat()} "
        f"(epoch ms {now_ms}). Treat times the user gives as their local wall-clock "
        f"unless they specify a timezone; ask if the date is ambiguous."
    )
    return create_react_agent(llm, tools, prompt=prompt)


async def stream_agent_reply(
    *,
    jwt: str,
    project_id: str,
    history: list[dict[str, str]],
    user_message: str,
) -> AsyncIterator[str]:
    """Yield the assistant's reply token-by-token. Tool-call turns are run silently;
    only natural-language text is emitted."""
    agent = await build_agent(jwt, project_id)
    messages = _to_messages(history, user_message)
    async for chunk, _meta in agent.astream(
        {"messages": messages}, stream_mode="messages"
    ):
        if isinstance(chunk, AIMessageChunk):
            text = _chunk_text(chunk)
            if text:
                yield text
