"""
supervisor/genie_client.py

Client module connecting to Databricks Managed MCP Genie Endpoints using the official MCP Python SDK.

Endpoint format: https://{host}/api/2.0/mcp/genie/{space_id}
Authenticates via Bearer PAT token using Streamable HTTP transport.
Surfaces all errors explicitly without swallowing exceptions.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

logger = logging.getLogger("supervisor.genie_client")


def _format_host(host: str) -> str:
    """Ensures host has standard https:// protocol prefix and no trailing slashes."""
    host_clean = host.strip().rstrip("/")
    if not host_clean.startswith("http://") and not host_clean.startswith("https://"):
        host_clean = f"https://{host_clean}"
    # Remove http:// if user gave http instead of https
    if host_clean.startswith("http://"):
        host_clean = "https://" + host_clean[len("http://") :]
    return host_clean.replace("https://", "")


async def ask_genie(space_id: str, question: str, host: str, token: str) -> str:
    """
    Connects to a Databricks Managed MCP Genie endpoint and asks a question.

    Args:
        space_id: Databricks Genie Space ID.
        question: Analytical question string.
        host: Databricks workspace host domain or URL.
        token: Databricks Personal Access Token (PAT).

    Returns:
        Text response from Genie.

    Raises:
        ValueError: If host, token, or space_id are missing.
        RuntimeError: If MCP connection fails, tool execution fails, or Genie returns an error.
    """
    if not space_id:
        raise ValueError("Genie space_id is required.")
    if not question:
        raise ValueError("Question string is required.")
    if not host:
        raise ValueError("Databricks host is required.")
    if not token:
        raise ValueError("Databricks token is required.")

    clean_host = _format_host(host)
    mcp_endpoint_url = f"https://{clean_host}/api/2.0/mcp/genie/{space_id}"

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "MediaAnalytics-Supervisor/1.0",
    }

    logger.info(f"Connecting to Genie MCP endpoint: {mcp_endpoint_url}")

    try:
        async with httpx.AsyncClient(headers=headers, timeout=60.0) as http_client:
            async with streamable_http_client(mcp_endpoint_url, http_client=http_client) as (
                read_stream,
                write_stream,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()

                    if not tools_result.tools:
                        raise RuntimeError(f"No MCP tools available on Genie space '{space_id}'.")

                    # Select tool (e.g. ask_genie, query, or first available tool)
                    tool = tools_result.tools[0]
                    tool_name = tool.name

                    # Build arguments matching schema or fallback to 'question' / 'query'
                    tool_args: Dict[str, Any] = {"question": question}
                    if tool.inputSchema and isinstance(tool.inputSchema, dict):
                        properties = tool.inputSchema.get("properties", {})
                        if "query" in properties and "question" not in properties:
                            tool_args = {"query": question}
                        elif "prompt" in properties and "question" not in properties:
                            tool_args = {"prompt": question}

                    logger.info(f"Executing MCP tool '{tool_name}' on Genie space '{space_id}'")
                    result = await session.call_tool(tool_name, tool_args)

                    if result.isError:
                        error_text = _extract_content_text(result.content)
                        raise RuntimeError(
                            f"Genie MCP tool '{tool_name}' returned error on space '{space_id}': {error_text}"
                        )

                    answer_text = _extract_content_text(result.content)
                    if not answer_text:
                        return f"Genie space {space_id} processed question but returned empty text."

                    return answer_text

    except Exception as exc:
        logger.error(f"Error calling Genie MCP space '{space_id}': {exc}", exc_info=True)
        raise RuntimeError(f"Failed to query Genie space '{space_id}' via MCP ({mcp_endpoint_url}): {str(exc)}") from exc


def _extract_content_text(content_list: Any) -> str:
    """Helper to extract text content from MCP content array."""
    if not content_list:
        return ""

    text_parts = []
    for item in content_list:
        if hasattr(item, "text"):
            text_parts.append(item.text)
        elif isinstance(item, dict) and "text" in item:
            text_parts.append(str(item["text"]))
        elif isinstance(item, str):
            text_parts.append(item)

    return "\n".join(text_parts).strip()


def ask_genie_sync(space_id: str, question: str, host: str, token: str) -> str:
    """Synchronous wrapper for ask_genie."""
    return asyncio.run(ask_genie(space_id=space_id, question=question, host=host, token=token))
