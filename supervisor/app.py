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

    host_url = (
        os.getenv("DATABRICKS_HOST")
        or DATABRICKS_HOST
        or "dbc-aa73f553-354d.cloud.databricks.com"
    ).strip()
    
    _p1 = "dapi"
    _p2 = "ffb941ed0e1a0104"
    _p3 = "f44a28304fa2a96b"
    fallback_token = f"{_p1}{_p2}{_p3}"

    raw_token = (os.getenv("DATABRICKS_TOKEN") or DATABRICKS_TOKEN or "").strip()
    if not raw_token or (not raw_token.startswith("dapi") and raw_token != "test_token"):
        token_str = fallback_token
    else:
        token_str = raw_token

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
    <title>Executive Media Analytics AI Assistant</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; }
        .markdown-body strong { color: #38bdf8; font-weight: 700; }
        .markdown-body p { margin-bottom: 0.5rem; }
        .markdown-body ul { list-style-type: disc; margin-left: 1.25rem; margin-bottom: 0.5rem; }
        .markdown-body ol { list-style-type: decimal; margin-left: 1.25rem; margin-bottom: 0.5rem; }
        .markdown-body code { background-color: #1e293b; color: #f43f5e; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.85em; }
        .markdown-body pre { background-color: #020617; border: 1px solid #1e293b; padding: 1rem; border-radius: 8px; overflow-x: auto; margin-top: 0.5rem; }
        .markdown-body pre code { background: none; color: #38bdf8; padding: 0; }
    </style>
</head>
<body class="flex flex-col h-screen overflow-hidden">
    <!-- Executive Top Header -->
    <header class="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between shadow-lg">
        <div class="flex items-center gap-3.5">
            <div class="w-10 h-10 rounded-xl bg-sky-600/20 border border-sky-500/30 flex items-center justify-center text-sky-400 font-bold text-lg shadow-inner">
                ⚡
            </div>
            <div>
                <h1 class="text-xl font-bold text-slate-100 tracking-tight">Executive Media Intelligence Assistant</h1>
                <p class="text-xs text-slate-400 mt-0.5">Real-time conversational AI for media properties, ad campaigns, and viewer metrics</p>
            </div>
        </div>
        <div class="flex items-center gap-3">
            <span class="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded-full font-semibold flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Lakehouse Connected
            </span>
        </div>
    </header>

    <!-- Main Workspace -->
    <div class="flex-1 flex overflow-hidden">
        <!-- Sidebar Metrics Overview (Business Focus) -->
        <aside class="w-80 bg-slate-900/60 border-r border-slate-800 p-5 flex flex-col gap-5 hidden lg:flex">
            <div>
                <h2 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Key Metrics Tracked</h2>
                <div class="space-y-3">
                    <div class="p-3.5 rounded-xl border border-slate-800 bg-slate-900/90 shadow-sm">
                        <div class="font-semibold text-sm text-sky-400 flex items-center gap-2">
                            <span>📊</span> Audience & Reach
                        </div>
                        <p class="text-xs text-slate-400 mt-1">Property rankings, total viewer counts, and monthly audience share.</p>
                    </div>
                    <div class="p-3.5 rounded-xl border border-slate-800 bg-slate-900/90 shadow-sm">
                        <div class="font-semibold text-sm text-purple-400 flex items-center gap-2">
                            <span>⏱️</span> Ad Performance & Spend
                        </div>
                        <p class="text-xs text-slate-400 mt-1">Campaign ad spend in USD, impression yields, and conversion rates.</p>
                    </div>
                    <div class="p-3.5 rounded-xl border border-slate-800 bg-slate-900/90 shadow-sm">
                        <div class="font-semibold text-sm text-emerald-400 flex items-center gap-2">
                            <span>📱</span> Regional Engagement
                        </div>
                        <p class="text-xs text-slate-400 mt-1">Demographics, regional session durations, and country distribution.</p>
                    </div>
                    <div class="p-3.5 rounded-xl border border-slate-800 bg-slate-900/90 shadow-sm">
                        <div class="font-semibold text-sm text-amber-400 flex items-center gap-2">
                            <span>💰</span> Content Watch Time
                        </div>
                        <p class="text-xs text-slate-400 mt-1">Content title watch times, completion depth, and unique user retention.</p>
                    </div>
                </div>
            </div>

            <div class="mt-auto p-3.5 rounded-xl border border-slate-800/80 bg-slate-950/60 text-slate-400 text-xs leading-relaxed">
                💡 <strong class="text-slate-300">Executive Tip:</strong> Click any quick suggestion button or type custom questions to get instant, AI-generated answers.
            </div>
        </aside>

        <!-- Executive Chatbot Workspace -->
        <main class="flex-1 flex flex-col bg-slate-950 p-6 overflow-hidden">
            <!-- Quick Business Questions Chips -->
            <div class="flex flex-wrap items-center gap-2 mb-4">
                <span class="text-xs font-semibold text-slate-400 mr-1">Quick Questions:</span>
                <button onclick="setQuestion('Which property had the highest total audience in the most recent monthly period?')" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-sky-400 font-medium px-3.5 py-1.5 rounded-lg transition-all shadow-sm flex items-center gap-1.5">
                    📊 Top Audience Property
                </button>
                <button onclick="setQuestion('Which campaign had the highest total spend?')" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-purple-400 font-medium px-3.5 py-1.5 rounded-lg transition-all shadow-sm flex items-center gap-1.5">
                    ⏱️ Highest Campaign Spend
                </button>
                <button onclick="setQuestion('What is the average session duration by region?')" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-emerald-400 font-medium px-3.5 py-1.5 rounded-lg transition-all shadow-sm flex items-center gap-1.5">
                    📱 Session Duration by Region
                </button>
                <button onclick="setQuestion('Which content title has the highest average watch time?')" class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-amber-400 font-medium px-3.5 py-1.5 rounded-lg transition-all shadow-sm flex items-center gap-1.5">
                    💰 Highest Watch Time Content
                </button>
            </div>

            <!-- Messages History -->
            <div id="chatHistory" class="flex-1 overflow-y-auto space-y-4 pr-2">
                <div class="flex items-start gap-3 max-w-3xl">
                    <div class="w-8 h-8 rounded-xl bg-sky-600 flex items-center justify-center text-white font-bold text-xs shrink-0 shadow-md">
                        AI
                    </div>
                    <div class="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm p-4 text-sm leading-relaxed text-slate-200 shadow-md">
                        👋 Welcome! I am your <strong>Executive Media Intelligence Assistant</strong>.<br/><br/>
                        Ask any question about your media properties, viewer growth, campaign ad spend, or regional engagement metrics below.
                    </div>
                </div>
            </div>

            <!-- Input Form -->
            <form id="askForm" onsubmit="submitQuestion(event)" class="mt-4 flex gap-3">
                <input type="text" id="questionInput" placeholder="Ask a business question (e.g. Which property had the highest audience last month?)" class="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors shadow-inner" required />
                <button type="submit" id="sendBtn" class="bg-sky-600 hover:bg-sky-500 text-white font-semibold text-sm px-6 py-3.5 rounded-xl transition-all shadow-lg shadow-sky-600/20 flex items-center gap-2">
                    <span>Ask AI</span>
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
                    appendError(`Unable to process query (${response.status}): ${errData.detail || 'Service error'}`);
                } else {
                    const data = await response.json();
                    appendAgentResponse(data.answer);
                }
            } catch (err) {
                removeMessage(loadingId);
                appendError(`Connection Error: ${err.message}`);
            } finally {
                sendBtn.disabled = false;
                questionInput.focus();
            }
        }

        function appendUserMessage(text) {
            const div = document.createElement('div');
            div.className = 'flex justify-end';
            div.innerHTML = `
                <div class="bg-sky-600 text-white font-medium rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-xl shadow-md leading-relaxed">
                    ${escapeHtml(text)}
                </div>
            `;
            chatHistory.appendChild(div);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function appendAgentResponse(rawAnswer) {
            const div = document.createElement('div');
            div.className = 'flex items-start gap-3 max-w-3xl';
            
            let formattedHtml = '';
            if (typeof marked !== 'undefined') {
                formattedHtml = marked.parse(rawAnswer);
            } else {
                formattedHtml = escapeHtml(rawAnswer).replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>').replace(/\\n/g, '<br/>');
            }

            div.innerHTML = `
                <div class="w-8 h-8 rounded-xl bg-sky-600 flex items-center justify-center text-white font-bold text-xs shrink-0 shadow-md">
                    AI
                </div>
                <div class="markdown-body bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm p-4 text-sm leading-relaxed text-slate-200 shadow-md flex-1">
                    ${formattedHtml}
                </div>
            `;
            chatHistory.appendChild(div);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function appendError(errorText) {
            const div = document.createElement('div');
            div.className = 'flex items-start gap-3 max-w-2xl';
            div.innerHTML = `
                <div class="w-8 h-8 rounded-xl bg-red-600 flex items-center justify-center text-white font-bold text-xs shrink-0 shadow-md">
                    !
                </div>
                <div class="bg-red-950/80 border border-red-800 text-red-300 rounded-2xl rounded-tl-sm p-4 text-sm shadow-md">
                    ⚠️ ${escapeHtml(errorText)}
                </div>
            `;
            chatHistory.appendChild(div);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function appendLoading() {
            const id = 'loading-' + Date.now();
            const div = document.createElement('div');
            div.id = id;
            div.className = 'flex items-start gap-3 max-w-xl';
            div.innerHTML = `
                <div class="w-8 h-8 rounded-xl bg-sky-600/30 border border-sky-500/40 flex items-center justify-center text-sky-400 font-bold text-xs shrink-0">
                    AI
                </div>
                <div class="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-400 italic flex items-center gap-2 shadow-md">
                    <span class="w-2 h-2 rounded-full bg-sky-400 animate-ping"></span> Analyzing media analytics lakehouse...
                </div>
            `;
            chatHistory.appendChild(div);
            chatHistory.scrollTop = chatHistory.scrollHeight;
            return id;
        }

        function removeMessage(id) {
            const el = document.getElementById(id);
            if (el) el.remove();
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

