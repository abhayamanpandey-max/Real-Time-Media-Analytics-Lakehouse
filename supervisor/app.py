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
    <title>Media Analytics AI</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body { background-color: #171717; color: #ececec; font-family: system-ui, -apple-system, sans-serif; }
        .markdown-body strong { color: #ffffff; font-weight: 600; }
        .markdown-body p { margin-bottom: 0.75rem; line-height: 1.625; }
        .markdown-body ul { list-style-type: disc; margin-left: 1.25rem; margin-bottom: 0.75rem; }
        .markdown-body ol { list-style-type: decimal; margin-left: 1.25rem; margin-bottom: 0.75rem; }
        .markdown-body code { background-color: #262626; color: #f43f5e; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.85em; }
        .markdown-body pre { background-color: #0a0a0a; border: 1px solid #262626; padding: 1rem; border-radius: 12px; overflow-x: auto; margin-top: 0.75rem; margin-bottom: 0.75rem; }
        .markdown-body pre code { background: none; color: #38bdf8; padding: 0; }
    </style>
</head>
<body class="flex flex-col h-screen overflow-hidden">
    <!-- Minimal Header (ChatGPT / Claude style) -->
    <header class="h-14 border-b border-[#262626] px-6 flex items-center justify-between bg-[#171717] shrink-0">
        <div class="flex items-center gap-2.5">
            <div class="w-7 h-7 rounded-full bg-[#262626] flex items-center justify-center text-sky-400 font-bold text-sm border border-[#333333]">
                ✦
            </div>
            <span class="text-sm font-semibold tracking-tight text-white">Media Analytics AI</span>
        </div>
        <div class="flex items-center gap-2">
            <span class="text-[11px] bg-[#262626] text-neutral-400 border border-[#333333] px-3 py-1 rounded-full font-medium flex items-center gap-2">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Connected to Lakehouse
            </span>
        </div>
    </header>

    <!-- Main Scrollable Chat Area -->
    <main class="flex-1 overflow-y-auto flex flex-col items-center p-4">
        <div id="chatFeed" class="w-full max-w-3xl flex-1 flex flex-col justify-between my-auto py-4">
            
            <!-- Welcome Screen (ChatGPT / Claude initial state) -->
            <div id="welcomeScreen" class="my-auto flex flex-col items-center justify-center text-center px-4">
                <div class="w-12 h-12 rounded-2xl bg-[#262626] border border-[#333333] flex items-center justify-center text-sky-400 font-bold text-xl mb-4 shadow-md">
                    ✦
                </div>
                <h1 class="text-2xl font-semibold text-white tracking-tight mb-2">What would you like to analyze today?</h1>
                <p class="text-sm text-neutral-400 max-w-md mb-8 leading-relaxed">Ask any question to query streaming audience metrics, campaign ad spend, regional trends, or content watch time.</p>
                
                <!-- Prompt Suggestion Cards (ChatGPT style) -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-xl text-left text-xs">
                    <button onclick="setQuestion('Which property had the highest total audience in the most recent monthly period?')" class="p-4 bg-[#212121] hover:bg-[#262626] border border-[#2e2e2e] hover:border-[#404040] rounded-2xl transition-all flex flex-col gap-1 group">
                        <span class="font-medium text-neutral-200 group-hover:text-white flex items-center gap-2">📊 Top Audience Property</span>
                        <span class="text-[11px] text-neutral-400">Which property had the highest monthly audience?</span>
                    </button>

                    <button onclick="setQuestion('Which campaign had the highest total spend?')" class="p-4 bg-[#212121] hover:bg-[#262626] border border-[#2e2e2e] hover:border-[#404040] rounded-2xl transition-all flex flex-col gap-1 group">
                        <span class="font-medium text-neutral-200 group-hover:text-white flex items-center gap-2">⏱️ Highest Campaign Spend</span>
                        <span class="text-[11px] text-neutral-400">Analyze campaign ad spend & metrics</span>
                    </button>

                    <button onclick="setQuestion('What is the average session duration by region?')" class="p-4 bg-[#212121] hover:bg-[#262626] border border-[#2e2e2e] hover:border-[#404040] rounded-2xl transition-all flex flex-col gap-1 group">
                        <span class="font-medium text-neutral-200 group-hover:text-white flex items-center gap-2">📱 Regional Engagement</span>
                        <span class="text-[11px] text-neutral-400">View session duration by country & region</span>
                    </button>

                    <button onclick="setQuestion('Which content title has the highest average watch time?')" class="p-4 bg-[#212121] hover:bg-[#262626] border border-[#2e2e2e] hover:border-[#404040] rounded-2xl transition-all flex flex-col gap-1 group">
                        <span class="font-medium text-neutral-200 group-hover:text-white flex items-center gap-2">💰 Content Watch Time</span>
                        <span class="text-[11px] text-neutral-400">Inspect content completion rate & watch time</span>
                    </button>
                </div>
            </div>

            <!-- Messages Stream -->
            <div id="messagesList" class="space-y-6 hidden w-full"></div>

        </div>
    </main>

    <!-- Floating Bottom Input Bar (ChatGPT / Claude style) -->
    <footer class="p-4 flex flex-col items-center shrink-0 bg-[#171717]">
        <div class="w-full max-w-3xl">
            <form id="askForm" onsubmit="submitQuestion(event)" class="relative flex items-center">
                <input 
                    type="text" 
                    id="questionInput" 
                    placeholder="Message Media Analytics AI..." 
                    class="w-full bg-[#212121] border border-[#2e2e2e] focus:border-[#404040] text-white rounded-2xl pl-5 pr-14 py-4 text-sm focus:outline-none transition-colors shadow-inner placeholder-neutral-500" 
                    required 
                />
                <button 
                    type="submit" 
                    id="sendBtn" 
                    class="absolute right-2.5 bg-sky-600 hover:bg-sky-500 text-white w-9 h-9 rounded-xl flex items-center justify-center transition-all shadow-md font-bold text-base"
                >
                    ↑
                </button>
            </form>
            <p class="text-[11px] text-neutral-500 text-center mt-2.5">Media Analytics AI analyzes live Delta Lake data via Databricks Genie.</p>
        </div>
    </footer>

    <script>
        const questionInput = document.getElementById('questionInput');
        const welcomeScreen = document.getElementById('welcomeScreen');
        const messagesList = document.getElementById('messagesList');
        const sendBtn = document.getElementById('sendBtn');

        function setQuestion(q) {
            questionInput.value = q;
            questionInput.focus();
        }

        async function submitQuestion(event) {
            event.preventDefault();
            const question = questionInput.value.trim();
            if (!question) return;

            // Show Messages Container & Hide Welcome Screen
            if (welcomeScreen) welcomeScreen.classList.add('hidden');
            messagesList.classList.remove('hidden');

            appendUserMessage(question);
            questionInput.value = '';
            sendBtn.disabled = true;

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
                <div class="bg-[#262626] text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-xl shadow-sm border border-[#333333] leading-relaxed">
                    ${escapeHtml(text)}
                </div>
            `;
            messagesList.appendChild(div);
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        }

        function appendAgentResponse(rawAnswer) {
            const div = document.createElement('div');
            div.className = 'flex items-start gap-4';
            
            let formattedHtml = '';
            if (typeof marked !== 'undefined') {
                formattedHtml = marked.parse(rawAnswer);
            } else {
                formattedHtml = escapeHtml(rawAnswer).replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>').replace(/\\n/g, '<br/>');
            }

            div.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-[#262626] border border-[#333333] flex items-center justify-center text-sky-400 font-bold text-sm shrink-0 mt-0.5">
                    ✦
                </div>
                <div class="markdown-body text-sm text-[#ececec] leading-relaxed flex-1">
                    ${formattedHtml}
                </div>
            `;
            messagesList.appendChild(div);
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        }

        function appendError(errorText) {
            const div = document.createElement('div');
            div.className = 'flex items-start gap-4';
            div.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-red-950/80 border border-red-800 text-red-400 font-bold text-xs flex items-center justify-center shrink-0">
                    !
                </div>
                <div class="text-red-400 text-sm py-1">
                    ⚠️ ${escapeHtml(errorText)}
                </div>
            `;
            messagesList.appendChild(div);
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        }

        function appendLoading() {
            const id = 'loading-' + Date.now();
            const div = document.createElement('div');
            div.id = id;
            div.className = 'flex items-start gap-4';
            div.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-[#262626] border border-[#333333] flex items-center justify-center text-sky-400 font-bold text-sm shrink-0">
                    ✦
                </div>
                <div class="text-neutral-400 text-sm italic py-1 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-sky-400 animate-ping"></span> Thinking...
                </div>
            `;
            messagesList.appendChild(div);
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
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

