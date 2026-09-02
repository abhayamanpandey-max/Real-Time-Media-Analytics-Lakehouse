"""
supervisor/app.py

FastAPI Application for the Standalone Supervisor Service.

Exposes:
  - POST /ask : Endpoint routing questions to Databricks Genie agents via MCP.
  - GET /health : Public healthcheck endpoint.
  - GET / : Minimal single-page HTML chat interface (vanilla HTML/JS).
"""

import logging
import os
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from supervisor.genie_client import ask_genie
from supervisor.router import route_question

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("supervisor.app")

app = FastAPI(
    title="Media Analytics Genie Supervisor",
    description="Multi-agent supervisor service routing NL questions to domain-specific Databricks Genie endpoints.",
    version="1.0.0",
)

# Configuration from environment with robust defaults
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "dbc-aa73f553-354d.cloud.databricks.com").strip()
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "").strip()

DEFAULT_SPACE_ID = os.getenv("GENIE_SPACE_ID", "01f1a1fd42bf12c9b418f72e196ce123").strip()

# Genie Space IDs mapping per domain
GENIE_SPACE_IDS: Dict[str, str] = {
    "audience_reach": (
        os.getenv("GENIE_SPACE_ID_AUDIENCE_REACH")
        or os.getenv("GENIE_SPACE_ID_AUDIENCE")
        or DEFAULT_SPACE_ID
    ).strip(),
    "engagement": (
        os.getenv("GENIE_SPACE_ID_ENGAGEMENT")
        or os.getenv("GENIE_SPACE_ID_AUDIENCE")
        or DEFAULT_SPACE_ID
    ).strip(),
    "composition": (
        os.getenv("GENIE_SPACE_ID_COMPOSITION")
        or os.getenv("GENIE_SPACE_ID_AUDIENCE")
        or DEFAULT_SPACE_ID
    ).strip(),
    "monetization": (
        os.getenv("GENIE_SPACE_ID_MONETIZATION")
        or os.getenv("GENIE_SPACE_ID_AUDIENCE")
        or DEFAULT_SPACE_ID
    ).strip(),
}


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    domain: str
    answer: str


@app.get("/health")
def healthcheck():
    """Public healthcheck endpoint."""
    return {"status": "ok", "service": "supervisor"}


@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(request: AskRequest):
    """
    Accepts natural language question, routes to domain agent, calls Databricks Genie via MCP.
    """
    question = request.question.strip() if request.question else ""
    if not question:
        raise HTTPException(status_code=400, detail="Question field cannot be empty.")

    # 1. Route question to domain
    domain = route_question(question)
    logger.info(f"Routed question '{question}' to domain: '{domain}'")

    # 2. Get space ID for domain with fallback
    space_id = (
        GENIE_SPACE_IDS.get(domain)
        or GENIE_SPACE_IDS.get("audience_reach")
        or DEFAULT_SPACE_ID
    )

    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        error_msg = "DATABRICKS_HOST or DATABRICKS_TOKEN env vars are missing on supervisor service."
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

    # 3. Call Databricks Genie MCP endpoint
    try:
        answer = await ask_genie(
            space_id=space_id,
            question=question,
            host=DATABRICKS_HOST,
            token=DATABRICKS_TOKEN,
        )
        return AskResponse(domain=domain, answer=answer)
    except Exception as exc:
        logger.error(f"Error querying Genie agent for domain '{domain}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Supervisor failed to query domain '{domain}' Genie agent: {str(exc)}",
        )


HTML_INTERFACE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Genie Supervisor Agent Portal</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: #0f172a;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        header {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-bottom: 1px solid #334155;
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 { font-size: 1.25rem; font-weight: 600; color: #38bdf8; }
        header p { font-size: 0.85rem; color: #94a3b8; }
        main {
            flex: 1;
            overflow-y: auto;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .chat-message {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            max-width: 800px;
            animation: fadeIn 0.3s ease-in-out;
        }
        .chat-message.user { align-self: flex-end; }
        .chat-message.agent { align-self: flex-start; }
        .message-bubble {
            padding: 1rem;
            border-radius: 12px;
            line-height: 1.5;
            font-size: 0.95rem;
        }
        .user .message-bubble {
            background-color: #2563eb;
            color: #ffffff;
            border-bottom-right-radius: 2px;
        }
        .agent .message-bubble {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #f8fafc;
            border-bottom-left-radius: 2px;
            white-space: pre-wrap;
        }
        .domain-badge {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.4rem;
            align-self: flex-start;
        }
        .badge-audience_reach { background-color: #0284c7; color: #ffffff; }
        .badge-engagement { background-color: #7c3aed; color: #ffffff; }
        .badge-composition { background-color: #059669; color: #ffffff; }
        .badge-monetization { background-color: #d97706; color: #ffffff; }
        .error-bubble {
            background-color: #7f1d1d;
            border: 1px solid #b91c1c;
            color: #fca5a5;
        }
        footer {
            background-color: #1e293b;
            border-top: 1px solid #334155;
            padding: 1rem 1.5rem;
        }
        .input-form {
            display: flex;
            gap: 0.75rem;
            max-width: 1000px;
            margin: 0 auto;
        }
        .input-form input {
            flex: 1;
            background-color: #0f172a;
            border: 1px solid #334155;
            color: #f8fafc;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 0.95rem;
            outline: none;
        }
        .input-form input:focus { border-color: #38bdf8; }
        .input-form button {
            background-color: #0284c7;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        .input-form button:hover { background-color: #0369a1; }
        .input-form button:disabled { background-color: #475569; cursor: not-allowed; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <header>
        <div>
            <h1>Databricks Genie Multi-Agent Supervisor</h1>
            <p>Routes analytical questions to domain agents (Audience, Engagement, Composition, Monetization)</p>
        </div>
    </header>

    <main id="chatHistory">
        <div class="chat-message agent">
            <div class="message-bubble">
                👋 Hello! Ask any question about your media analytics lakehouse (e.g. audience reach, engagement trends, user demographics, or ad monetization). I will automatically route it to the appropriate Databricks Genie domain agent.
            </div>
        </div>
    </main>

    <footer>
        <form class="input-form" id="askForm" onsubmit="submitQuestion(event)">
            <input type="text" id="questionInput" placeholder="Ask a question (e.g., Which property had the highest audience last month?)" required />
            <button type="submit" id="sendBtn">Send</button>
        </form>
    </footer>

    <script>
        const questionInput = document.getElementById('questionInput');
        const chatHistory = document.getElementById('chatHistory');
        const sendBtn = document.getElementById('sendBtn');

        async function submitQuestion(event) {
            event.preventDefault();
            const question = questionInput.value.trim();
            if (!question) return;

            // Render user question
            appendMessage('user', question);
            questionInput.value = '';
            sendBtn.disabled = true;

            // Render loading message
            const loadingId = appendLoading();

            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: question })
                });

                removeMessage(loadingId);

                if (!response.ok) {
                    const errData = await response.json().catch(() => ({ detail: response.statusText }));
                    appendError(`Error (${response.status}): ${errData.detail || 'Failed to fetch answer'}`);
                } else {
                    const data = await response.json();
                    appendAgentResponse(data.domain, data.answer);
                }
            } catch (err) {
                removeMessage(loadingId);
                appendError(`Network / Service Error: ${err.message}`);
            } finally {
                sendBtn.disabled = false;
                questionInput.focus();
            }
        }

        function appendMessage(sender, text) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `chat-message ${sender}`;
            msgDiv.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
            chatHistory.appendChild(msgDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function appendAgentResponse(domain, answer) {
            const msgDiv = document.createElement('div');
            msgDiv.className = 'chat-message agent';
            const badgeClass = `badge-${domain}` || 'badge-audience_reach';
            const domainTitle = (domain || 'UNKNOWN').replace('_', ' ').toUpperCase();
            
            msgDiv.innerHTML = `
                <span class="domain-badge ${badgeClass}">Routed to: ${domainTitle}</span>
                <div class="message-bubble">${escapeHtml(answer)}</div>
            `;
            chatHistory.appendChild(msgDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function appendError(errorText) {
            const msgDiv = document.createElement('div');
            msgDiv.className = 'chat-message agent';
            msgDiv.innerHTML = `<div class="message-bubble error-bubble">⚠️ ${escapeHtml(errorText)}</div>`;
            chatHistory.appendChild(msgDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function appendLoading() {
            const id = 'loading-' + Date.now();
            const msgDiv = document.createElement('div');
            msgDiv.id = id;
            msgDiv.className = 'chat-message agent';
            msgDiv.innerHTML = `<div class="message-bubble">⏳ Routing question to domain agent & querying Databricks Genie via MCP...</div>`;
            chatHistory.appendChild(msgDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight;
            return id;
        }

        function removeMessage(id) {
            const el = document.getElementById(id);
            if (el) el.remove();
        }

        function escapeHtml(str) {
            return str
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    """Serves minimal single-page HTML chat interface."""
    return HTMLResponse(content=HTML_INTERFACE, status_code=200)
