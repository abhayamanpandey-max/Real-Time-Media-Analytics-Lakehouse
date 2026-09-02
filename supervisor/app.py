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
from typing import Dict, Optional

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

# Configuration from environment with fallback defaults
DATABRICKS_HOST = (
    os.getenv("DATABRICKS_HOST")
    or "dbc-aa73f553-354d.cloud.databricks.com"
).strip()

DATABRICKS_TOKEN = (
    os.getenv("DATABRICKS_TOKEN")
    or "4fb61313f73ef71f3cf8b18a26bb952facaf71ca6c1693d9787a6ee0e30fe4ae"
).strip()

DEFAULT_SPACE_ID = "01f1a1fd42bf12c9b418f72e196ce123"

# Genie Space IDs mapping per domain with fallback defaults
GENIE_SPACE_IDS: Dict[str, str] = {
    "audience_reach": (
        os.getenv("GENIE_SPACE_ID_AUDIENCE_REACH")
        or os.getenv("GENIE_SPACE_ID_AUDIENCE")
        or os.getenv("GENIE_SPACE_ID")
        or "01f1a1fd42bf12c9b418f72e196ce123"
    ).strip(),
    "engagement": (
        os.getenv("GENIE_SPACE_ID_ENGAGEMENT")
        or "01f1a6065b871342b326e101c2469fb2"
    ).strip(),
    "composition": (
        os.getenv("GENIE_SPACE_ID_COMPOSITION")
        or "01f1a6061e7110a69b5c9b4d3ccc16b4"
    ).strip(),
    "monetization": (
        os.getenv("GENIE_SPACE_ID_MONETIZATION")
        or "01f1a605b30a1a06ae28b8f2fc484f56"
    ).strip(),
}


class AskRequest(BaseModel):
    question: str
    domain: Optional[str] = None


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

    # 1. Route question to domain (or use target domain if explicitly passed)
    if request.domain and request.domain in GENIE_SPACE_IDS:
        domain = request.domain
        logger.info(f"Using explicitly selected domain: '{domain}'")
    else:
        domain = route_question(question)
        logger.info(f"Routed question '{question}' to domain: '{domain}'")

    # 2. Get space ID for domain with fallback
    space_id = (
        GENIE_SPACE_IDS.get(domain)
        or GENIE_SPACE_IDS.get("audience_reach")
        or DEFAULT_SPACE_ID
    )

    host_url = DATABRICKS_HOST if DATABRICKS_HOST else "dbc-aa73f553-354d.cloud.databricks.com"
    token_str = DATABRICKS_TOKEN if DATABRICKS_TOKEN else "4fb61313f73ef71f3cf8b18a26bb952facaf71ca6c1693d9787a6ee0e30fe4ae"

    # 3. Call Databricks Genie MCP endpoint
    try:
        answer = await ask_genie(
            space_id=space_id,
            question=question,
            host=host_url,
            token=token_str,
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
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; }
        .markdown-body strong { color: #38bdf8; font-weight: 700; }
        .markdown-body p { margin-bottom: 0.5rem; }
        .markdown-body ul { list-style-type: disc; margin-left: 1.25rem; margin-bottom: 0.5rem; }
        .markdown-body ol { list-style-type: decimal; margin-left: 1.25rem; margin-bottom: 0.5rem; }
        .markdown-body code { background-color: #1e293b; color: #f43f5e; padding: 0.1rem 0.3rem; border-radius: 4px; font-size: 0.85em; }
    </style>
</head>
<body class="flex flex-col h-screen overflow-hidden">
    <!-- Top Navigation Header -->
    <header class="bg-slate-900 border-b border-slate-800 px-6 py-3.5 flex items-center justify-between shadow-lg">
        <div>
            <div class="flex items-center gap-3">
                <span class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></span>
                <h1 class="text-xl font-bold text-sky-400 tracking-tight">Databricks Genie Multi-Agent Supervisor</h1>
            </div>
            <p class="text-xs text-slate-400 mt-0.5">Routes NL questions across 4 domain agents: Audience Reach, Engagement, Composition & Monetization</p>
        </div>
        <div class="flex items-center gap-2">
            <span class="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded-full font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-emerald-400"></span> 4 Managed MCP Agents Online
            </span>
        </div>
    </header>

    <!-- Main Container -->
    <div class="flex-1 flex overflow-hidden">
        <!-- Sidebar Domain Agents Overview (Interactive Clickable Cards) -->
        <aside class="w-80 bg-slate-900/60 border-r border-slate-800 p-4 flex flex-col gap-4 hidden lg:flex">
            <div class="flex items-center justify-between">
                <h2 class="text-xs font-bold uppercase tracking-wider text-slate-400">Domain Agents (Click to Target)</h2>
                <button onclick="selectAgent('auto')" id="autoBtn" class="text-[10px] bg-sky-600 text-white font-semibold px-2 py-0.5 rounded transition-all">Auto-Route</button>
            </div>
            <div class="space-y-2.5">
                <!-- Agent Card 1: Audience & Reach -->
                <div onclick="selectAgent('audience_reach')" id="card-audience_reach" class="agent-card p-3 rounded-xl border border-sky-500/40 bg-slate-900/90 cursor-pointer hover:border-sky-400 transition-all shadow-md">
                    <div class="flex items-center justify-between">
                        <div class="font-semibold text-sm text-sky-400 flex items-center gap-2">
                            <span>📊</span> Audience & Reach
                        </div>
                        <span id="badge-audience_reach" class="text-[9px] bg-sky-500/20 text-sky-300 px-1.5 py-0.5 rounded font-bold uppercase">Active</span>
                    </div>
                    <p class="text-xs text-slate-400 mt-1">Property rankings, viewer counts, audience share & trends.</p>
                    <div class="text-[10px] font-mono text-slate-500 mt-2">Space ID: 01f1a1fd42bf12...</div>
                </div>

                <!-- Agent Card 2: Engagement -->
                <div onclick="selectAgent('engagement')" id="card-engagement" class="agent-card p-3 rounded-xl border border-slate-800 bg-slate-900/40 cursor-pointer hover:border-purple-400 transition-all">
                    <div class="flex items-center justify-between">
                        <div class="font-semibold text-sm text-purple-400 flex items-center gap-2">
                            <span>⏱️</span> Engagement
                        </div>
                        <span id="badge-engagement" class="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-bold uppercase">Standby</span>
                    </div>
                    <p class="text-xs text-slate-400 mt-1">Average watch time, session duration & completion rates.</p>
                    <div class="text-[10px] font-mono text-slate-500 mt-2">Space ID: 01f1a6061e7110...</div>
                </div>

                <!-- Agent Card 3: Composition -->
                <div onclick="selectAgent('composition')" id="card-composition" class="agent-card p-3 rounded-xl border border-slate-800 bg-slate-900/40 cursor-pointer hover:border-emerald-400 transition-all">
                    <div class="flex items-center justify-between">
                        <div class="font-semibold text-sm text-emerald-400 flex items-center gap-2">
                            <span>📱</span> Composition
                        </div>
                        <span id="badge-composition" class="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-bold uppercase">Standby</span>
                    </div>
                    <p class="text-xs text-slate-400 mt-1">Demographics, platforms, device split & overlap index.</p>
                    <div class="text-[10px] font-mono text-slate-500 mt-2">Space ID: 01f1a605b30a1a...</div>
                </div>

                <!-- Agent Card 4: Monetization -->
                <div onclick="selectAgent('monetization')" id="card-monetization" class="agent-card p-3 rounded-xl border border-slate-800 bg-slate-900/40 cursor-pointer hover:border-amber-400 transition-all">
                    <div class="flex items-center justify-between">
                        <div class="font-semibold text-sm text-amber-400 flex items-center gap-2">
                            <span>💰</span> Monetization
                        </div>
                        <span id="badge-monetization" class="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-bold uppercase">Standby</span>
                    </div>
                    <p class="text-xs text-slate-400 mt-1">Ad revenue, CPM yields, ARPU & fill rate analytics.</p>
                    <div class="text-[10px] font-mono text-slate-500 mt-2">Space ID: 01f1a6065b8713...</div>
                </div>
            </div>
        </aside>

        <!-- Chat Workspace -->
        <main class="flex-1 flex flex-col bg-slate-950 p-6 overflow-hidden">
            <!-- Domain Selection Tabs -->
            <div class="flex flex-wrap items-center gap-2 mb-4">
                <span class="text-xs font-semibold text-slate-400 mr-1">Agent Mode:</span>
                <button onclick="selectAgent('auto')" id="tab-auto" class="text-xs bg-sky-600 text-white font-medium px-3 py-1.5 rounded-lg transition-all">⚡ Auto-Route</button>
                <button onclick="selectAgent('audience_reach')" id="tab-audience_reach" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-sky-400 px-3 py-1.5 rounded-lg transition-all">📊 Audience & Reach</button>
                <button onclick="selectAgent('engagement')" id="tab-engagement" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-purple-400 px-3 py-1.5 rounded-lg transition-all">⏱️ Engagement</button>
                <button onclick="selectAgent('composition')" id="tab-composition" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-emerald-400 px-3 py-1.5 rounded-lg transition-all">📱 Composition</button>
                <button onclick="selectAgent('monetization')" id="tab-monetization" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-amber-400 px-3 py-1.5 rounded-lg transition-all">💰 Monetization</button>
            </div>

            <!-- Messages History -->
            <div id="chatHistory" class="flex-1 overflow-y-auto space-y-4 pr-2">
                <div class="flex flex-col items-start max-w-2xl">
                    <div class="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm p-4 text-sm leading-relaxed text-slate-200 shadow-md">
                        👋 Welcome to the **Databricks Genie Multi-Agent Supervisor** portal!<br/><br/>
                        Select an agent card on the left or type your question below. The supervisor automatically routes questions to the corresponding Databricks Managed MCP Genie Agent!
                    </div>
                </div>
            </div>

            <!-- Input Bar -->
            <form id="askForm" onsubmit="submitQuestion(event)" class="mt-4 flex gap-3">
                <input type="text" id="questionInput" placeholder="Ask a question (e.g. Which property had the highest audience last month?)" class="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors" required />
                <button type="submit" id="sendBtn" class="bg-sky-600 hover:bg-sky-500 text-white font-semibold text-sm px-6 py-3 rounded-xl transition-all shadow-lg shadow-sky-600/20 flex items-center gap-2">
                    <span>Send Question</span>
                </button>
            </form>
        </main>
    </div>

    <script>
        let selectedDomain = 'auto';
        const questionInput = document.getElementById('questionInput');
        const chatHistory = document.getElementById('chatHistory');
        const sendBtn = document.getElementById('sendBtn');

        const SAMPLE_QUESTIONS = {
            'audience_reach': 'Which property had the highest total audience in the most recent monthly period?',
            'engagement': 'What is the average watch time per session on mobile?',
            'composition': 'What is the audience profile breakdown by platform for property XYZ?',
            'monetization': 'What is the total ad revenue generated across all properties this quarter?',
            'auto': 'Which property had the highest total audience last month?'
        };

        function selectAgent(domain) {
            selectedDomain = domain;
            
            // Update Card Highlights
            const domains = ['audience_reach', 'engagement', 'composition', 'monetization'];
            domains.forEach(d => {
                const card = document.getElementById('card-' + d);
                const badge = document.getElementById('badge-' + d);
                const tab = document.getElementById('tab-' + d);
                
                if (d === domain) {
                    if (card) { card.className = 'agent-card p-3 rounded-xl border border-sky-400 bg-slate-900/90 shadow-lg ring-1 ring-sky-400/50 cursor-pointer transition-all'; }
                    if (badge) { badge.className = 'text-[9px] bg-sky-500 text-white px-1.5 py-0.5 rounded font-bold uppercase'; badge.innerText = 'TARGETED'; }
                    if (tab) { tab.className = 'text-xs bg-sky-600 text-white font-semibold px-3 py-1.5 rounded-lg transition-all shadow'; }
                } else {
                    if (card) { card.className = 'agent-card p-3 rounded-xl border border-slate-800 bg-slate-900/40 cursor-pointer hover:border-slate-700 transition-all'; }
                    if (badge) { badge.className = 'text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-bold uppercase'; badge.innerText = 'STANDBY'; }
                    if (tab) { tab.className = 'text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 px-3 py-1.5 rounded-lg transition-all'; }
                }
            });

            const autoBtn = document.getElementById('autoBtn');
            const tabAuto = document.getElementById('tab-auto');
            if (domain === 'auto') {
                if (autoBtn) autoBtn.className = 'text-[10px] bg-sky-600 text-white font-semibold px-2 py-0.5 rounded shadow';
                if (tabAuto) tabAuto.className = 'text-xs bg-sky-600 text-white font-semibold px-3 py-1.5 rounded-lg transition-all shadow';
            } else {
                if (autoBtn) autoBtn.className = 'text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded hover:text-white';
                if (tabAuto) tabAuto.className = 'text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 px-3 py-1.5 rounded-lg transition-all';
            }

            if (SAMPLE_QUESTIONS[domain]) {
                questionInput.value = SAMPLE_QUESTIONS[domain];
                questionInput.focus();
            }
        }

        async function submitQuestion(event) {
            event.preventDefault();
            const question = questionInput.value.trim();
            if (!question) return;

            appendUserMessage(question);
            questionInput.value = '';
            sendBtn.disabled = true;

            const loadingId = appendLoading();

            try {
                const payload = { question: question };
                if (selectedDomain !== 'auto') {
                    payload.domain = selectedDomain;
                }

                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
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
            div.innerHTML = `<div class="bg-sky-600 text-white font-medium rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-xl shadow-md">${escapeHtml(text)}</div>`;
            chatHistory.appendChild(div);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function appendAgentResponse(domain, rawAnswer) {
            const div = document.createElement('div');
            div.className = 'flex flex-col items-start max-w-3xl';
            const badge = getDomainBadge(domain);
            
            // Format Markdown properly using marked library if available, else format basic bold/bullets
            let formattedHtml = '';
            if (typeof marked !== 'undefined') {
                formattedHtml = marked.parse(rawAnswer);
            } else {
                formattedHtml = escapeHtml(rawAnswer).replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>').replace(/\\n/g, '<br/>');
            }

            div.innerHTML = `
                <div class="mb-1">${badge}</div>
                <div class="markdown-body bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm p-4 text-sm leading-relaxed text-slate-200 shadow-md">${formattedHtml}</div>
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
            div.innerHTML = `<div class="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-400 italic flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-sky-400 animate-ping"></span> Routing question to target Genie agent & querying Databricks via Managed MCP...</div>`;
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

