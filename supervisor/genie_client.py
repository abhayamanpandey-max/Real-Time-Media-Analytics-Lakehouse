"""
supervisor/genie_client.py

Client module connecting to Databricks Genie agents using MCP and REST API fallbacks.
Handles PAT token formatting (dapi prefix auto-detection) and surfaces errors clearly.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

logger = logging.getLogger("supervisor.genie_client")


def _format_host(host: str) -> str:
    """Ensures host has standard domain format with no protocol or trailing slashes."""
    host_clean = host.strip().rstrip("/")
    if host_clean.startswith("https://"):
        host_clean = host_clean[len("https://") :]
    if host_clean.startswith("http://"):
        host_clean = host_clean[len("http://") :]
    return host_clean.rstrip("/")


def _get_token_candidates(token: str) -> list[str]:
    """Generates candidate PAT token strings (both as-is and with dapi prefix)."""
    token_clean = token.strip()
    candidates = [token_clean]
    if not token_clean.startswith("dapi"):
        candidates.append(f"dapi{token_clean}")
    return candidates


async def ask_genie(space_id: str, question: str, host: str, token: str) -> str:
    """
    Connects to a Databricks Genie agent (via MCP or REST API fallback) and asks a question.

    Args:
        space_id: Databricks Genie Space ID.
        question: Analytical question string.
        host: Databricks workspace host domain or URL.
        token: Databricks Personal Access Token (PAT).

    Returns:
        Text response from Genie.
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
    token_candidates = _get_token_candidates(token)

    last_error: Optional[Exception] = None

    # Try each token candidate with MCP endpoint first
    for tok in token_candidates:
        try:
            answer = await _ask_genie_mcp(space_id=space_id, question=question, clean_host=clean_host, token=tok)
            if answer:
                return answer
        except Exception as exc:
            logger.warning(f"MCP endpoint attempt failed for token candidate: {exc}")
            last_error = exc

    # Fallback to Databricks Genie REST API (start-conversation)
    for tok in token_candidates:
        try:
            answer = await _ask_genie_rest(space_id=space_id, question=question, clean_host=clean_host, token=tok)
            if answer:
                return answer
        except Exception as exc:
            logger.warning(f"REST API fallback attempt failed for token candidate: {exc}")
            last_error = exc

    err_str = str(last_error)
    if "403" in err_str or "401" in err_str or "Forbidden" in err_str or "Unauthorized" in err_str:
        raise RuntimeError(
            "Databricks PAT Token Authentication Error (403 Forbidden / 401 Unauthorized). "
            "Please generate a fresh Personal Access Token in your Databricks Workspace Settings "
            "(User Settings -> Access Tokens -> Generate New Token) and set DATABRICKS_TOKEN in your .env file."
        )

    raise RuntimeError(f"Failed to query Genie space '{space_id}' via MCP/REST API: {err_str}")


async def _ask_genie_mcp(space_id: str, question: str, clean_host: str, token: str) -> str:
    """Queries Genie space via Databricks Managed MCP Endpoint."""
    mcp_endpoint_url = f"https://{clean_host}/api/2.0/mcp/genie/{space_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "MediaAnalytics-Supervisor/1.0",
    }

    async with httpx.AsyncClient(headers=headers, timeout=45.0) as http_client:
        async with streamable_http_client(mcp_endpoint_url, http_client=http_client) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_result = await session.list_tools()

                if not tools_result.tools:
                    raise RuntimeError(f"No MCP tools available on Genie space '{space_id}'.")

                tool = tools_result.tools[0]
                tool_name = tool.name
                tool_args: Dict[str, Any] = {"question": question}

                if tool.inputSchema and isinstance(tool.inputSchema, dict):
                    props = tool.inputSchema.get("properties", {})
                    if "query" in props and "question" not in props:
                        tool_args = {"query": question}
                    elif "prompt" in props and "question" not in props:
                        tool_args = {"prompt": question}

                result = await session.call_tool(tool_name, tool_args)
                if result.isError:
                    error_text = _extract_content_text(result.content)
                    raise RuntimeError(f"Genie MCP tool error: {error_text}")

                return _extract_content_text(result.content)


async def _ask_genie_rest(space_id: str, question: str, clean_host: str, token: str) -> str:
    """Fallback query via Databricks Genie REST API (/start-conversation)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    start_url = f"https://{clean_host}/api/2.0/genie/spaces/{space_id}/start-conversation"

    async with httpx.AsyncClient(headers=headers, timeout=20.0) as client:
        start_resp = await client.post(start_url, json={"content": question})
        start_resp.raise_for_status()
        data = start_resp.json()

        conv_id = data.get("conversation_id")
        msg_id = data.get("message_id")
        if not conv_id or not msg_id:
            raise RuntimeError(f"Genie start-conversation response missing IDs: {data}")

        poll_url = f"https://{clean_host}/api/2.0/genie/spaces/{space_id}/conversations/{conv_id}/messages/{msg_id}"

        # Poll until complete (up to 45s)
        for _ in range(30):
            await asyncio.sleep(1.5)
            poll_resp = await client.get(poll_url)
            poll_resp.raise_for_status()
            poll_data = poll_resp.json()

            status = poll_data.get("status")
            if status in ("COMPLETED", "EXECUTED"):
                answer_parts = []
                sql_part = ""

                for att in poll_data.get("attachments", []):
                    if isinstance(att, dict):
                        # Extract text answer content
                        if "text" in att:
                            text_obj = att["text"]
                            if isinstance(text_obj, dict):
                                content = text_obj.get("content") or text_obj.get("text")
                                purpose = text_obj.get("purpose", "")
                                if content and purpose == "TEXT_ATTACHMENT_PURPOSE_ANSWER":
                                    answer_parts.insert(0, content)
                                elif content and purpose != "FOLLOW_UP_QUESTION":
                                    answer_parts.append(content)
                            elif isinstance(text_obj, str):
                                answer_parts.append(text_obj)

                        # Extract generated SQL query
                        if "query" in att:
                            q_obj = att["query"]
                            if isinstance(q_obj, dict) and "query" in q_obj:
                                sql_part = f"```sql\n{q_obj['query'].strip()}\n```"

                full_answer = "\n\n".join(answer_parts).strip()
                if full_answer:
                    # Strip any trailing Generated SQL Query block if present
                    clean_answer = full_answer.split("**Generated SQL Query:**")[0].strip()
                    return clean_answer if clean_answer else full_answer

                return f"Query completed successfully for space '{space_id}'."
            elif status in ("FAILED", "CANCELLED", "ERROR"):
                raise RuntimeError(f"Genie space '{space_id}' query failed with status: {status}")

        raise TimeoutError(f"Genie query timed out waiting for space '{space_id}'.")


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
