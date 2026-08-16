#!/usr/bin/env python3
"""LORNA 2 Home Assistant MCP bridge.

Connects LORNA's Ollama model to a Home Assistant MCP server using
Streamable HTTP. The MCP server supplies the tools; Ollama decides when
to call them. No Home Assistant credentials are stored in this file.

Environment:
  LORNA_HA_MCP_URL   MCP endpoint, default http://homeassistant:8123/api/mcp
  LORNA_HA_TOKEN     optional Home Assistant long-lived access token
  LORNA_MCP_TIMEOUT  request timeout in seconds, default 30
"""

import asyncio
import json
import os
from typing import Any

import httpx2
import ollama
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

DEFAULT_MCP_URL = "http://homeassistant:8123/api/mcp"


def _headers() -> dict[str, str]:
    token = os.environ.get("LORNA_HA_TOKEN", "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _http_client(timeout: float) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(
        headers=_headers(),
        follow_redirects=True,
        timeout=httpx2.Timeout(timeout, read=timeout),
    )


def _mcp_tool_to_ollama(tool: Any) -> dict[str, Any]:
    schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
    if hasattr(schema, "model_dump"):
        schema = schema.model_dump(exclude_none=True)
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "Home Assistant MCP tool",
            "parameters": schema,
        },
    }


def _content_to_text(result: Any) -> str:
    chunks: list[str] = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text is not None:
            chunks.append(text)
        elif hasattr(item, "model_dump"):
            chunks.append(json.dumps(item.model_dump(), ensure_ascii=False))
        else:
            chunks.append(str(item))
    if getattr(result, "structuredContent", None) is not None:
        structured = result.structuredContent
        if isinstance(structured, str):
            chunks.append(structured)
        else:
            chunks.append(json.dumps(structured, ensure_ascii=False))
    if getattr(result, "isError", False):
        chunks.insert(0, "MCP tool reported an error.")
    return "\n".join(chunks) or "(No result returned.)"


async def _run(user_input: str, model: str, system_prompt: str | None = None) -> str:
    url = os.environ.get("LORNA_HA_MCP_URL", DEFAULT_MCP_URL).strip()
    timeout = float(os.environ.get("LORNA_MCP_TIMEOUT", "30"))

    async with _http_client(timeout) as http_client:
        async with streamable_http_client(url=url, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                tools = [_mcp_tool_to_ollama(t) for t in listed.tools]

                messages: list[dict[str, Any]] = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": user_input})

                for _ in range(8):
                    response = ollama.chat(model=model, messages=messages, tools=tools or None)
                    message = response.get("message", {})
                    tool_calls = message.get("tool_calls") or []
                    if not tool_calls:
                        return message.get("content", "")

                    messages.append(message)
                    for call in tool_calls:
                        function = call.get("function", {})
                        name = function.get("name", "")
                        arguments = function.get("arguments", {})
                        if isinstance(arguments, str):
                            try:
                                arguments = json.loads(arguments)
                            except json.JSONDecodeError:
                                arguments = {"input": arguments}
                        try:
                            result = await session.call_tool(name, arguments=arguments)
                            content = _content_to_text(result)
                        except Exception as exc:
                            content = f"MCP tool call failed: {type(exc).__name__}: {exc}"
                        messages.append({"role": "tool", "content": content})

                return "MCP tool loop exceeded 8 rounds; stopping safely."


def chat_with_mcp(user_input: str, model: str, system_prompt: str | None = None) -> str:
    """Synchronous adapter used by LORNA's existing interactive loop."""
    try:
        return asyncio.run(_run(user_input, model, system_prompt))
    except Exception as exc:
        return f"MCP connection error: {type(exc).__name__}: {exc}"


def mcp_status() -> str:
    """Return a short connectivity/tool inventory report."""
    async def _status() -> str:
        url = os.environ.get("LORNA_HA_MCP_URL", DEFAULT_MCP_URL).strip()
        timeout = float(os.environ.get("LORNA_MCP_TIMEOUT", "10"))
        async with _http_client(timeout) as http_client:
            async with streamable_http_client(url=url, http_client=http_client) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    names = [t.name for t in result.tools]
                    return f"Connected to {url}\nMCP tools: {len(names)}\n" + "\n".join(f"  - {n}" for n in names)

    try:
        return asyncio.run(_status())
    except Exception as exc:
        return f"MCP status error: {type(exc).__name__}: {exc}"
