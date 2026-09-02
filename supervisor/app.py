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
    <title>Databricks Genie Multi-Agent Supervisor Portal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; }
    </style>
</head>
<body class="flex flex-col h-screen overflow-hidden">
    <!-- Top Navigation Header -->
    <header class="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between shadow-lg">
        <div>
            <div class="flex items-center gap-3">
                <span class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></span>
                <h1 class="text-xl font-bold text-sky-400 tracking-tight">Databricks Genie Multi-Agent Supervisor</h1>
            </div>
            <p class="text-xs text-slate-400 mt-0.5">Routes NL questions across 4 domain agents: Audience Reach, Engagement, Composition & Monetization</p>
        </div>
        <div class="flex items-center gap-2">
            <span class="text-xs bg-sky-500/20 text-sky-400 border border-sky-500/30 px-3 py-1 rounded-full font-medium">EC2 Port 8001 Live</span>
        </div>
    </header>

    <!-- Main Container -->
    <div class="flex-1 flex overflow-hidden">
        <!-- Sidebar Domain Agents Overview -->
        <aside class="w-72 bg-slate-900/50 border-r border-slate-800 p-4 flex flex-col gap-4 hidden md:flex">
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-400">Domain Agents Overview</h2>
            <div class="space-y-3">
                <div class="p-3 rounded-xl border border-slate-800 bg-slate-900/80 hover:border-sky-500/30 transition-all">
                    <div class="font-semibold text-sm text-sky-400 flex items-center gap-2">
                        <span>📊</span> Audience & Reach
                    </div>
                    <p class="text-xs text-slate-400 mt-1">Property rankings, viewer counts, audience share & trends.</p>
                </div>
                <div class="p-3 rounded-xl border border-slate-800 bg-slate-900/80 hover:border-purple-500/30 transition-all">
                    <div class="font-semibold text-sm text-purple-400 flex items-center gap-2">
                        <span>⏱️</span> Engagement
                    </div>
                    <p class="text-xs text-slate-400 mt-1">Average watch time, session duration & video completion rates.</p>
                </div>
                <div class="p-3 rounded-xl border border-slate-800 bg-slate-900/80 hover:border-emerald-500/30 transition-all">
                    <div class="font-semibold text-sm text-emerald-400 flex items-center gap-2">
                        <span>📱</span> Composition
                    </div>
                    <p class="text-xs text-slate-400 mt-1">Demographics, platforms, device split & audience overlap index.</p>
                </div>
                <div class="p-3 rounded-xl border border-slate-800 bg-slate-900/80 hover:border-amber-500/30 transition-all">
                    <div class="font-semibold text-sm text-amber-400 flex items-center gap-2">
                        <span>💰</span> Monetization
                    </div>
                    <p class="text-xs text-slate-400 mt-1">Ad revenue, CPM yields, ARPU & fill rate analytics.</p>
                </div>
            </div>
        </aside>

        <!-- Chat Workspace -->
        <main class="flex-1 flex flex-col bg-slate-950 p-6 overflow-hidden">
            <!-- Quick Suggestion Chips -->
            <div class="flex flex-wrap gap-2 mb-4">
                <button onclick="setQuestion('Which property had the highest total audience in the most recent monthly period?')" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-lg transition-colors">
                    💡 Highest Audience Property
                </button>
                <button onclick="setQuestion('What is the average watch time per session on mobile?')" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-lg transition-colors">
                    💡 Watch Time Trends
                </button>
                <button onclick="setQuestion('What is the audience profile breakdown by platform for property XYZ?')" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-lg transition-colors">
                    💡 Platform Breakdown
                </button>
                <button onclick="setQuestion('What is the total ad revenue generated across all properties this quarter?')" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-lg transition-colors">
                    💡 Ad Revenue & CPM
                </button>
            </div>

            <!-- Messages History -->
            <div id="chatHistory" class="flex-1 overflow-y-auto space-y-4 pr-2">
                <div class="flex flex-col items-start max-w-2xl">
                    <div class="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm p-4 text-sm leading-relaxed text-slate-200">
                        👋 Welcome to the **Databricks Genie Multi-Agent Supervisor** portal! Type any question below. I will inspect your query, determine the domain, route to the target Genie Agent, and query Databricks via Managed MCP.
                    </div>
                </div>
            </div>

            <!-- Input Bar -->
            <form id="askForm" onsubmit="submitQuestion(event)" class="mt-4 flex gap-3">
                <input type="text" id="questionInput" placeholder="Ask a question (e.g. Which property had the highest audience last month?)" class="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors" required />
                <button type="submit" id="sendBtn" class="bg-sky-600 hover:bg-sky-500 text-white font-semibold text-sm px-6 py-3 rounded-xl transition-all shadow-lg shadow-sky-600/20">
                    Send Question
                </button>
            </form>
        </main>
    </div>

    <script>
        const questionInput = document.getElementById('questionInput');
        const chatHistory = document.getElementById('chatHistory');
        const sendBtn = document.getElementById('sendBtn');

        function setQuestion(q) {
            questionInput.value = q;
            questionInput.focus();
        }

        async function submitQuestion(event) {
            event.preventDefault();
            const question = questionInput.value.trim();
            if (!question) return;

            // Render User Message
            appendUserMessage(question);
            questionInput.value = '';
            sendBtn.disabled = true;

            // Render Loading Message
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
                    appendError(`Error (${response.status}): ${errData.detail || 'Failed to query agent'}`);
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

        function appendUserMessage(text) {
            const div = document.createElement('div');
            div.className = 'flex flex-col items-end';
            div.innerHTML = `<div class="bg-sky-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-xl shadow-md">${escapeHtml(text)}</div>`;
            chatHistory.appendChild(div);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function appendAgentResponse(domain, answer) {
            const div = document.createElement('div');
            div.className = 'flex flex-col items-start max-w-3xl';
            const badge = getDomainBadge(domain);
            div.innerHTML = `
                <div class="mb-1">${badge}</div>
                <div class="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm p-4 text-sm leading-relaxed text-slate-200 whitespace-pre-wrap shadow-md">${escapeHtml(answer)}</div>
            `;
            chatHistory.appendChild(div);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function appendError(errorText) {
            const div = document.createElement('div');
            div.className = 'flex flex-col items-start max-w-2xl';
            div.innerHTML = `<div class="bg-red-950/80 border border-red-800 text-red-300 rounded-2xl rounded-tl-sm p-4 text-sm shadow-md">⚠️ ${escapeHtml(errorText)}</div>`;
            chatHistory.appendChild(div);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function appendLoading() {
            const id = 'loading-' + Date.now();
            const div = document.createElement('div');
            div.id = id;
            div.className = 'flex flex-col items-start max-w-xl';
            div.innerHTML = `<div class="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-400 italic flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-sky-400 animate-ping"></span> Routing question to domain agent & querying Databricks Genie via MCP...</div>`;
            chatHistory.appendChild(div);
            chatHistory.scrollTop = chatHistory.scrollHeight;
            return id;
        }

        function removeMessage(id) {
            const el = document.getElementById(id);
            if (el) el.remove();
        }

        function getDomainBadge(domain) {
            const d = (domain || 'audience_reach').toLowerCase();
            if (d.includes('monetization')) return '<span class="inline-block bg-amber-500/20 text-amber-400 border border-amber-500/30 font-bold text-[10px] tracking-wider uppercase px-2.5 py-1 rounded-full">Routed to: Monetization</span>';
            if (d.includes('composition')) return '<span class="inline-block bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold text-[10px] tracking-wider uppercase px-2.5 py-1 rounded-full">Routed to: Composition</span>';
            if (d.includes('engagement')) return '<span class="inline-block bg-purple-500/20 text-purple-400 border border-purple-500/30 font-bold text-[10px] tracking-wider uppercase px-2.5 py-1 rounded-full">Routed to: Engagement</span>';
            return '<span class="inline-block bg-sky-500/20 text-sky-400 border border-sky-500/30 font-bold text-[10px] tracking-wider uppercase px-2.5 py-1 rounded-full">Routed to: Audience & Reach</span>';
        }

        function escapeHtml(str) {
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    """Serves minimal single-page HTML chat interface."""
    return HTMLResponse(content=HTML_INTERFACE, status_code=200)
