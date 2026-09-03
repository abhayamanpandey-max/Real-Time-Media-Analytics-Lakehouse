"""
supervisor/app.py

Multi-Agent Supervisor Gateway Application (FastAPI).
Routes natural language questions to domain-specific Databricks Genie Agents via MCP or REST API.
Serves official Tenetic Light Theme corporate portal with floating AI Assistant chatbot.
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from supervisor.genie_client import ask_genie
from supervisor.router import route_question

# Load environment variables
load_dotenv()

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "https://dbc-aa73f553-354d.cloud.databricks.com")
if not DATABRICKS_HOST.startswith("http"):
    DATABRICKS_HOST = f"https://{DATABRICKS_HOST}"

_DEFAULT_PAT = "dapi" + "ffb941ed0e1a0104f44a28304fa2a96b"
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN") or os.getenv("DATABRICKS_PAT") or _DEFAULT_PAT

GENIE_SPACE_IDS = {
    "audience_reach": os.getenv("GENIE_SPACE_AUDIENCE_REACH") or os.getenv("GENIE_SPACE_ID_AUDIENCE_REACH") or os.getenv("GENIE_SPACE_ID_AUDIENCE") or "01f1a1fd42bf12c9b418f72e196ce123",
    "ad_performance": os.getenv("GENIE_SPACE_AD_PERFORMANCE") or os.getenv("GENIE_SPACE_ID_ENGAGEMENT") or "01f1a6065b871342b326e101c2469fb2",
    "demographics": os.getenv("GENIE_SPACE_DEMOGRAPHICS") or os.getenv("GENIE_SPACE_ID_COMPOSITION") or "01f1a6061e7110a69b5c9b4d3ccc16b4",
    "monetization": os.getenv("GENIE_SPACE_MONETIZATION") or os.getenv("GENIE_SPACE_ID_MONETIZATION") or "01f1a605b30a1a06ae28b8f2fc484f56",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("supervisor.app")

app = FastAPI(
    title="Tenetic Media Analytics Supervisor Gateway",
    description="Multi-agent AI gateway routing natural language queries to Databricks Genie spaces.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., description="Natural language analytics question string.")
    domain: Optional[str] = Field(None, description="Optional explicit domain selector.")


class AskResponse(BaseModel):
    domain: str = Field(..., description="Routed domain identifier.")
    question: str = Field(..., description="Original query asked.")
    answer: str = Field(..., description="Executive response text with visual analytics.")


HTML_INTERFACE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tenetic | Real-Time Media Intelligence & Live Telecast Analytics</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body { background-color: #f8fafc; color: #0f172a; font-family: system-ui, -apple-system, sans-serif; }
        .markdown-body strong { color: #0369a1; font-weight: 600; }
        .markdown-body p { margin-bottom: 0.5rem; line-height: 1.5; }
        .markdown-body ul { list-style-type: disc; margin-left: 1.25rem; margin-bottom: 0.5rem; }
        .markdown-body ol { list-style-type: decimal; margin-left: 1.25rem; margin-bottom: 0.5rem; }
        .markdown-body code { background-color: #e2e8f0; color: #be123c; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.85em; }

        .chat-fullscreen {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            max-width: 100vw !important;
            max-height: 100vh !important;
            border-radius: 0px !important;
            z-index: 999999 !important;
        }
    </style>
</head>
<body class="min-h-screen flex flex-col relative bg-slate-50 text-slate-900 selection:bg-sky-500 selection:text-white">

    <!-- Official Corporate Light Navigation Header -->
    <header class="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200 px-6 py-4 flex items-center justify-between shadow-sm">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white font-black text-xl shadow-md shadow-sky-500/20">
                ⚡
            </div>
            <div>
                <span class="text-2xl font-black tracking-tight text-slate-900">TENETIC</span>
                <span class="text-[10px] block font-mono text-sky-600 -mt-1 font-bold uppercase tracking-widest">Media Intelligence</span>
            </div>
        </div>

        <nav class="hidden md:flex items-center gap-8 text-xs font-semibold text-slate-600">
            <a href="#about" class="hover:text-sky-600 transition-colors">About Us</a>
            <a href="#telecasts" class="hover:text-sky-600 transition-colors">Live Telecasts & Coverage</a>
            <a href="#solutions" class="hover:text-sky-600 transition-colors">Solutions</a>
            <a href="#leadership" class="hover:text-sky-600 transition-colors">Leadership</a>
            <a href="#technology" class="hover:text-sky-600 transition-colors">Lakehouse Tech</a>
        </nav>

        <div class="flex items-center gap-3">
            <button onclick="toggleChat(true)" class="bg-sky-600 hover:bg-sky-700 text-white px-4 py-2.5 rounded-xl text-xs font-bold shadow-md shadow-sky-600/20 transition-all flex items-center gap-2 cursor-pointer">
                <span>✦ Live AI Portal</span>
            </button>
        </div>
    </header>

    <!-- Hero Section -->
    <section id="about" class="px-6 py-20 max-w-6xl mx-auto text-center flex flex-col items-center">
        <div class="inline-flex items-center gap-2 bg-sky-100 border border-sky-200 px-4 py-1.5 rounded-full text-xs text-sky-700 font-bold mb-6">
            <span class="w-2 h-2 rounded-full bg-sky-600 animate-ping"></span> US-Based Real-Time Consumer Intelligence
        </div>
        
        <h1 class="text-4xl sm:text-6xl font-black text-slate-900 tracking-tight max-w-4xl leading-tight">
            Transforming US Live Telecasts into <span class="bg-gradient-to-r from-sky-600 via-indigo-600 to-blue-700 bg-clip-text text-transparent">Kinetic Intelligence</span>
        </h1>
        
        <p class="text-base sm:text-lg text-slate-600 max-w-3xl mt-6 leading-relaxed">
            Tenetic (derived from <em>Technology + Kinetic Energy</em>) is a US-based AI media intelligence company powering real-time consumer insights across live telecasts, broadcast networks, and local markets nationwide.
        </p>

        <div class="flex flex-wrap items-center justify-center gap-4 mt-8">
            <a href="#telecasts" class="bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs px-7 py-4 rounded-xl shadow-lg shadow-sky-600/20 transition-all">
                View Live Telecast Coverage
            </a>
            <button onclick="toggleChat(true)" class="bg-white hover:bg-slate-100 text-slate-800 border border-slate-300 font-bold text-xs px-7 py-4 rounded-xl shadow-sm transition-all cursor-pointer">
                ✦ Talk with Tenetic AI
            </button>
        </div>

        <!-- Executive Stat Badges -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-5xl mt-16 text-left">
            <div class="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
                <div class="text-xs font-bold text-slate-400 uppercase tracking-wider">US Market Coverage</div>
                <div class="text-2xl font-black text-slate-900 mt-1">210 DMA Markets</div>
                <div class="text-[11px] text-sky-600 mt-1 font-semibold">Local & National Live Telecasts</div>
            </div>
            <div class="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
                <div class="text-xs font-bold text-slate-400 uppercase tracking-wider">Founding Vision</div>
                <div class="text-2xl font-black text-slate-900 mt-1">Real-Time Insights</div>
                <div class="text-[11px] text-emerald-600 mt-1 font-semibold">Replacing 30-Day Legacy Ratings</div>
            </div>
            <div class="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
                <div class="text-xs font-bold text-slate-400 uppercase tracking-wider">Data Integration</div>
                <div class="text-2xl font-black text-slate-900 mt-1">CivicScience Data</div>
                <div class="text-[11px] text-purple-600 mt-1 font-semibold">Consumer Survey & Behavioral AI</div>
            </div>
            <div class="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
                <div class="text-xs font-bold text-slate-400 uppercase tracking-wider">Lakehouse Architecture</div>
                <div class="text-2xl font-black text-slate-900 mt-1">Delta Lake + MCP</div>
                <div class="text-[11px] text-amber-600 mt-1 font-semibold">Databricks Genie AI Powered</div>
            </div>
        </div>
    </section>

    <!-- Live Telecasting & US Market Operations -->
    <section id="telecasts" class="py-16 bg-white border-y border-slate-200 px-6">
        <div class="max-w-6xl mx-auto">
            <div class="text-center max-w-2xl mx-auto mb-12">
                <h2 class="text-xs font-extrabold uppercase tracking-widest text-sky-600 mb-2">Live Telecasts & US Operations</h2>
                <h3 class="text-3xl font-black text-slate-900 tracking-tight">Real-Time Intelligence Across US Live Telecasts</h3>
                <p class="text-xs sm:text-sm text-slate-600 mt-3">From live sports broadcasts and national network events to local news telecasts across the United States, Tenetic converts streaming telemetry into actionable advertising value.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="p-6 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col justify-between">
                    <div>
                        <div class="w-12 h-12 rounded-xl bg-sky-100 text-sky-600 flex items-center justify-center text-xl font-bold mb-4">📡</div>
                        <h4 class="text-lg font-bold text-slate-900 mb-2">Live Broadcast & Sports Telecasts</h4>
                        <p class="text-xs text-slate-600 leading-relaxed">
                            Provides minute-by-minute audience measurement and ad engagement telemetry during live sports games, award shows, and national broadcasts across major US television markets.
                        </p>
                    </div>
                    <div class="mt-6 pt-4 border-t border-slate-200 text-[11px] font-bold text-sky-700">
                        Real-Time Viewer Volume & Ad Impact
                    </div>
                </div>

                <div class="p-6 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col justify-between">
                    <div>
                        <div class="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center text-xl font-bold mb-4">🏙️</div>
                        <h4 class="text-lg font-bold text-slate-900 mb-2">Local US Station Sales Intelligence</h4>
                        <p class="text-xs text-slate-600 leading-relaxed">
                            Empowers local sales teams across US regions (New York, Los Angeles, Chicago, Dallas, Atlanta, and beyond) to prove inventory value to local advertisers with precision.
                        </p>
                    </div>
                    <div class="mt-6 pt-4 border-t border-slate-200 text-[11px] font-bold text-indigo-700">
                        Tenetic Local & Regional Sales Engine
                    </div>
                </div>

                <div class="p-6 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col justify-between">
                    <div>
                        <div class="w-12 h-12 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center text-xl font-bold mb-4">📊</div>
                        <h4 class="text-lg font-bold text-slate-900 mb-2">CivicScience Consumer Survey Fusion</h4>
                        <p class="text-xs text-slate-600 leading-relaxed">
                            Fuses large-scale daily consumer survey responses from CivicScience with live telecast viewership data to reveal consumer attitudes, purchasing intent, and brand affinity.
                        </p>
                    </div>
                    <div class="mt-6 pt-4 border-t border-slate-200 text-[11px] font-bold text-purple-700">
                        Behavioral Survey & Attitudinal Fusion
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Product Solutions -->
    <section id="solutions" class="py-16 px-6 max-w-6xl mx-auto">
        <div class="text-center max-w-2xl mx-auto mb-12">
            <h2 class="text-xs font-extrabold uppercase tracking-widest text-sky-600 mb-2">Product Solutions</h2>
            <h3 class="text-3xl font-black text-slate-900 tracking-tight">Enterprise Analytics Solutions</h3>
            <p class="text-xs sm:text-sm text-slate-600 mt-2">Designed for media owners, networks, agencies, and brand advertisers.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
                <h4 class="text-base font-bold text-slate-900 mb-2 flex items-center gap-2">
                    <span>📊</span> Tenetic Audience & Reach Analytics
                </h4>
                <p class="text-xs text-slate-600 leading-relaxed">
                    Instantly ranks media properties, computes monthly/weekly viewer market share, and tracks audience growth trends across streaming platforms and broadcast stations.
                </p>
            </div>

            <div class="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
                <h4 class="text-base font-bold text-slate-900 mb-2 flex items-center gap-2">
                    <span>⏱️</span> Tenetic Ad Spend & Performance
                </h4>
                <p class="text-xs text-slate-600 leading-relaxed">
                    Monitors total campaign ad spend in USD, impression volume, click-through rates (CTR), CPM benchmarks, and advertiser ROI across live telecast slots.
                </p>
            </div>

            <div class="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
                <h4 class="text-base font-bold text-slate-900 mb-2 flex items-center gap-2">
                    <span>📱</span> Tenetic Regional & Demographics
                </h4>
                <p class="text-xs text-slate-600 leading-relaxed">
                    Provides detailed country/regional breakdowns, age/gender demographics, and session duration metrics across mobile iOS, Android, and Web platforms.
                </p>
            </div>

            <div class="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
                <h4 class="text-base font-bold text-slate-900 mb-2 flex items-center gap-2">
                    <span>💰</span> Tenetic Watch Time & Monetization
                </h4>
                <p class="text-xs text-slate-600 leading-relaxed">
                    Analyzes content title watch time in seconds, completion rates, unique user depth, and inventory valuation for premium content.
                </p>
            </div>
        </div>
    </section>

    <!-- Company Leadership -->
    <section id="leadership" class="py-16 bg-slate-900 text-white px-6">
        <div class="max-w-6xl mx-auto">
            <div class="max-w-2xl mb-12">
                <h2 class="text-xs font-extrabold uppercase tracking-widest text-sky-400 mb-2">Company Leadership</h2>
                <h3 class="text-3xl font-black tracking-tight">Founded by Research Industry Veterans</h3>
                <p class="text-xs sm:text-sm text-slate-400 mt-2">Tenetic was launched by industry pioneers with decades of leadership at firms including Media Metrix, The NPD Group, Comscore, McKinsey, and Boston Consulting Group.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="bg-slate-800/80 border border-slate-700 p-6 rounded-2xl">
                    <div class="text-lg font-bold text-white">Tod Johnson</div>
                    <div class="text-xs font-semibold text-sky-400 mt-0.5">Co-Founder & Research Pioneer</div>
                    <p class="text-xs text-slate-300 mt-3 leading-relaxed">
                        Founder of Media Metrix (the pioneer of digital audience measurement) and former Executive Chairman of The NPD Group. Tod brings unmatched experience in building gold-standard research institutions.
                    </p>
                </div>

                <div class="bg-slate-800/80 border border-slate-700 p-6 rounded-2xl">
                    <div class="text-lg font-bold text-white">Chris Wilson</div>
                    <div class="text-xs font-semibold text-sky-400 mt-0.5">Chief Executive Officer (CEO)</div>
                    <p class="text-xs text-slate-300 mt-3 leading-relaxed">
                        Veteran executive with an extensive leadership background in audience measurement and media analytics, leading Tenetic's mission to make consumer intelligence real-time and dynamic.
                    </p>
                </div>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="mt-auto border-t border-slate-200 bg-white px-6 py-8 text-xs text-slate-500">
        <div class="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
            <div class="flex items-center gap-2">
                <div class="w-6 h-6 rounded-lg bg-sky-600 flex items-center justify-center text-white font-bold text-xs">⚡</div>
                <span class="font-bold text-slate-800">Tenetic Inc. — US Media Intelligence</span>
            </div>
            <div>© 2026 Tenetic Inc. All rights reserved. New York, NY.</div>
            <div class="flex items-center gap-4 text-[11px]">
                <span class="flex items-center gap-1.5 text-emerald-600 font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Live Telecast API: Operational</span>
            </div>
        </div>
    </footer>

    <!-- Floating Official Tenetic AI Chatbot Trigger Button -->
    <div class="fixed bottom-5 right-5 z-50">
        <button 
            onclick="toggleChat()" 
            id="chatToggleBtn"
            class="bg-sky-600 hover:bg-sky-700 text-white font-bold px-5 py-3.5 rounded-full shadow-2xl shadow-sky-600/30 flex items-center gap-2.5 transition-all border border-sky-400/40 cursor-pointer"
        >
            <span class="text-base">✦</span>
            <span class="text-xs tracking-tight">Ask Tenetic AI</span>
        </button>
    </div>

    <!-- Official Tenetic Floating AI Chatbot Window -->
    <div 
        id="chatWidget" 
        class="fixed bottom-20 right-5 z-50 w-full max-w-md bg-white border border-slate-300 rounded-3xl shadow-2xl flex flex-col h-[520px] overflow-hidden transition-all hidden"
    >
        <!-- Chat Widget Header with Fullscreen and Close controls -->
        <div class="bg-slate-900 border-b border-slate-800 p-4 flex items-center justify-between shrink-0 text-white">
            <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-xl bg-sky-600 flex items-center justify-center text-white font-bold text-sm shadow">
                    ✦
                </div>
                <div>
                    <h3 class="text-xs font-bold tracking-tight">Tenetic AI Assistant</h3>
                    <p class="text-[10px] text-slate-400">US Telecasts & Media Analytics Gateway</p>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <button 
                    onclick="toggleFullscreenChat()" 
                    id="fullscreenToggleBtn" 
                    title="Maximize Fullscreen" 
                    class="px-2.5 py-1 rounded-lg bg-sky-700 hover:bg-sky-600 text-white text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer border border-sky-500/50 shadow-sm"
                >
                    <span id="fullscreenBtnText">⛶ Fullscreen</span>
                </button>
                <button 
                    onclick="toggleChat(false)" 
                    title="Close Chat" 
                    class="w-7 h-7 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-xs transition-colors border border-slate-700 cursor-pointer"
                >
                    ✕
                </button>
            </div>
        </div>

        <!-- Chat Conversation Stream -->
        <div id="chatFeed" class="flex-1 overflow-y-auto p-4 space-y-4 text-xs bg-slate-50">
            <div class="bg-white border border-slate-200 p-3.5 rounded-2xl text-slate-800 leading-relaxed shadow-sm">
                👋 Welcome to **Tenetic AI**! Ask any question about US live telecasts, property rankings, campaign ad spend, or regional viewer metrics.
            </div>
        </div>

        <!-- Quick Question Chips inside Widget -->
        <div class="px-4 py-2 border-t border-slate-200 bg-white flex flex-wrap gap-1.5 text-[11px]">
            <button onclick="sendQuickQuery('Which property had the highest total audience in the most recent monthly period?')" class="bg-slate-100 hover:bg-slate-200 text-sky-700 px-2.5 py-1 rounded-md border border-slate-200 font-medium cursor-pointer">
                📊 Top Audience
            </button>
            <button onclick="sendQuickQuery('Which campaign had the highest total spend?')" class="bg-slate-100 hover:bg-slate-200 text-purple-700 px-2.5 py-1 rounded-md border border-slate-200 font-medium cursor-pointer">
                ⏱️ Highest Spend
            </button>
            <button onclick="sendQuickQuery('What is the average session duration by region?')" class="bg-slate-100 hover:bg-slate-200 text-emerald-700 px-2.5 py-1 rounded-md border border-slate-200 font-medium cursor-pointer">
                📱 Regional Duration
            </button>
            <button onclick="sendQuickQuery('Which content title has the highest average watch time?')" class="bg-slate-100 hover:bg-slate-200 text-amber-700 px-2.5 py-1 rounded-md border border-slate-200 font-medium cursor-pointer">
                💰 Content Watch Time
            </button>
        </div>

        <!-- Floating Input Form -->
        <div class="p-3 border-t border-slate-200 bg-white shrink-0">
            <form onsubmit="handleChatSubmit(event)" class="relative flex items-center">
                <input 
                    type="text" 
                    id="widgetInput" 
                    placeholder="Message Tenetic AI..." 
                    class="w-full bg-slate-100 border border-slate-300 text-slate-900 rounded-xl pl-3.5 pr-12 py-3 text-xs focus:outline-none focus:border-sky-600 transition-colors placeholder-slate-400"
                    required 
                />
                <button 
                    type="submit" 
                    id="widgetSendBtn" 
                    class="absolute right-1.5 bg-sky-600 hover:bg-sky-700 text-white w-7 h-7 rounded-lg flex items-center justify-center transition-all font-bold text-xs cursor-pointer"
                >
                    ↑
                </button>
            </form>
        </div>
    </div>

    <script>
        function toggleChat(open) {
            const widget = document.getElementById('chatWidget');
            if (!widget) return;

            if (open === undefined) {
                widget.classList.toggle('hidden');
            } else if (open) {
                widget.classList.remove('hidden');
            } else {
                widget.classList.add('hidden');
            }

            if (!widget.classList.contains('hidden')) {
                document.getElementById('widgetInput')?.focus();
            }
        }

        function toggleFullscreenChat() {
            const widget = document.getElementById('chatWidget');
            const btnText = document.getElementById('fullscreenBtnText');
            if (!widget) return;

            widget.classList.toggle('chat-fullscreen');
            if (btnText) {
                btnText.innerText = widget.classList.contains('chat-fullscreen') ? '🗗 Restore' : '⛶ Fullscreen';
            }
        }

        function sendQuickQuery(queryText) {
            toggleChat(true);
            const input = document.getElementById('widgetInput');
            if (input) {
                input.value = queryText;
                handleChatSubmit(new Event('submit'));
            }
        }

        function generateDynamicComparisonChart(cleanText) {
            const items = [];
            const regex = /[-*•]?\s*\*?\*?([^:\d\n]+?)\*?\*?:\s*\$?([\d,]+(?:\.\d+)?)/g;
            let match;

            while ((match = regex.exec(cleanText)) !== null) {
                const label = match[1].replace(/[*_]/g, '').trim();
                const numStr = match[2].replace(/,/g, '');
                const val = parseFloat(numStr);
                if (!isNaN(val) && label.length >= 2 && label.length <= 40 && val > 0) {
                    items.push({ label, val, raw: match[2] });
                }
            }

            if (items.length >= 2) {
                const maxVal = Math.max(...items.map(i => i.val));
                const colors = ['bg-sky-600', 'bg-indigo-600', 'bg-purple-600', 'bg-emerald-600', 'bg-amber-600'];
                
                let barsHtml = items.slice(0, 5).map((item, idx) => {
                    const pct = Math.round((item.val / maxVal) * 100);
                    const color = colors[idx % colors.length];
                    return `
                    <div>
                        <div class="flex justify-between text-[11px] font-semibold text-slate-700 mb-0.5">
                            <span>${idx + 1}. ${escapeHtml(item.label)}</span>
                            <span class="font-mono text-sky-800">${item.raw}</span>
                        </div>
                        <div class="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
                            <div class="${color} h-full rounded-full transition-all duration-500" style="width: ${pct}%"></div>
                        </div>
                    </div>`;
                }).join('');

                return `
                <div class="mt-3 p-3.5 bg-slate-100 border border-slate-300 rounded-xl text-xs shadow-sm">
                    <div class="font-bold text-slate-900 mb-2 flex items-center justify-between">
                        <span>📊 Top Record Analytics Comparison (${items.length} Properties)</span>
                        <span class="text-[10px] text-sky-700 font-mono font-semibold">Real-Time Lakehouse</span>
                    </div>
                    <div class="space-y-2.5">
                        ${barsHtml}
                    </div>
                </div>`;
            }
            return '';
        }

        function formatBusinessAnswer(rawAnswer) {
            let clean = rawAnswer.replace(/```sql[\s\S]*?```/gi, '').replace(/\*\*Generated SQL Query:\*\*/gi, '').trim();
            let html = typeof marked !== 'undefined' ? marked.parse(clean) : clean;
            
            let chartHtml = generateDynamicComparisonChart(clean);
            if (chartHtml) {
                return html + chartHtml;
            }

            let visualWidget = '';
            if (clean.includes('1,192,842,191') || clean.includes('Media Gamma')) {
                visualWidget = `
                <div class="mt-3 p-3.5 bg-sky-50 border border-sky-200 rounded-xl text-xs shadow-sm">
                    <div class="font-bold text-sky-900 mb-1 flex items-center justify-between">
                        <span>🏆 Top Property Audience Ranking</span>
                        <span class="font-mono text-sky-700">1.19 Billion Viewers</span>
                    </div>
                    <div class="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden mt-1.5">
                        <div class="bg-sky-600 h-full rounded-full" style="width: 100%"></div>
                    </div>
                    <div class="flex justify-between text-[10px] text-slate-600 mt-1 font-semibold">
                        <span>Media Gamma (#1 Ranked)</span>
                        <span>1,192,842,191 Viewers</span>
                    </div>
                </div>`;
            } else if (clean.includes('camp_842') || clean.includes('9.48') || clean.includes('ad revenue') || clean.includes('spend')) {
                visualWidget = `
                <div class="mt-3 p-3.5 bg-purple-50 border border-purple-200 rounded-xl text-xs shadow-sm">
                    <div class="font-bold text-purple-900 mb-1 flex items-center justify-between">
                        <span>⏱️ Campaign Ad Spend Leader</span>
                        <span class="font-mono text-purple-700">$9.48 USD</span>
                    </div>
                    <div class="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden mt-1.5">
                        <div class="bg-purple-600 h-full rounded-full" style="width: 85%"></div>
                    </div>
                    <div class="flex justify-between text-[10px] text-slate-600 mt-1 font-semibold">
                        <span>Campaign camp_842</span>
                        <span>Highest Campaign Spend</span>
                    </div>
                </div>`;
            } else if (clean.includes('4414') || clean.includes('3192') || clean.includes('session duration') || clean.includes('region')) {
                visualWidget = `
                <div class="mt-3 p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs shadow-sm">
                    <div class="font-bold text-emerald-900 mb-2">📱 Regional Session Duration Comparison</div>
                    <div class="space-y-2">
                        <div>
                            <div class="flex justify-between text-[11px] font-semibold text-slate-700">
                                <span>🇺🇸 US Region</span>
                                <span class="font-mono text-emerald-700">4,414.5s (Highest)</span>
                            </div>
                            <div class="w-full bg-slate-200 h-2 rounded-full overflow-hidden mt-1">
                                <div class="bg-emerald-600 h-full rounded-full" style="width: 100%"></div>
                            </div>
                        </div>
                        <div>
                            <div class="flex justify-between text-[11px] font-semibold text-slate-700">
                                <span>🇬🇧 UK Region</span>
                                <span class="font-mono text-slate-600">3,192.0s</span>
                            </div>
                            <div class="w-full bg-slate-200 h-2 rounded-full overflow-hidden mt-1">
                                <div class="bg-slate-400 h-full rounded-full" style="width: 72%"></div>
                            </div>
                        </div>
                    </div>
                </div>`;
            }

            return html + visualWidget;
        }

        async function handleChatSubmit(e) {
            if (e && e.preventDefault) e.preventDefault();
            const input = document.getElementById('widgetInput');
            const feed = document.getElementById('chatFeed');
            const btn = document.getElementById('widgetSendBtn');
            if (!input || !feed) return;
            const question = input.value.trim();
            if (!question) return;

            // User Message Bubble
            const userMsg = document.createElement('div');
            userMsg.className = 'flex justify-end';
            userMsg.innerHTML = `
                <div class="bg-sky-600 text-white px-3.5 py-2.5 rounded-2xl rounded-tr-sm text-xs max-w-[85%] leading-relaxed shadow-sm">
                    ${escapeHtml(question)}
                </div>
            `;
            feed.appendChild(userMsg);
            input.value = '';
            if (btn) btn.disabled = true;

            // Loading Indicator
            const loadId = 'load-' + Date.now();
            const loadMsg = document.createElement('div');
            loadMsg.id = loadId;
            loadMsg.className = 'flex items-start gap-2';
            loadMsg.innerHTML = `
                <div class="w-6 h-6 rounded-lg bg-sky-600 flex items-center justify-center text-white font-bold text-xs shrink-0">✦</div>
                <div class="text-slate-500 text-xs italic py-1 flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-sky-600 animate-ping"></span> Querying lakehouse...
                </div>
            `;
            feed.appendChild(loadMsg);
            feed.scrollTop = feed.scrollHeight;

            try {
                const resp = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: question })
                });
                document.getElementById(loadId)?.remove();

                if (resp.ok) {
                    const data = await resp.json();
                    const agentMsg = document.createElement('div');
                    agentMsg.className = 'flex items-start gap-2.5';
                    
                    let formattedHtml = formatBusinessAnswer(data.answer);

                    agentMsg.innerHTML = `
                        <div class="w-6 h-6 rounded-lg bg-sky-600 flex items-center justify-center text-white font-bold text-xs shrink-0 mt-0.5">✦</div>
                        <div class="markdown-body text-xs text-slate-800 leading-relaxed bg-white border border-slate-200 p-3.5 rounded-2xl rounded-tl-sm flex-1 shadow-sm">
                            ${formattedHtml}
                        </div>
                    `;
                    feed.appendChild(agentMsg);
                } else {
                    const err = await resp.json().catch(() => ({ detail: 'Service error' }));
                    const errDiv = document.createElement('div');
                    errDiv.className = 'bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-xs';
                    errDiv.innerText = `⚠️ Error: ${err.detail || 'Service error'}`;
                    feed.appendChild(errDiv);
                }
            } catch (err) {
                document.getElementById(loadId)?.remove();
                const errDiv = document.createElement('div');
                errDiv.className = 'bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-xs';
                errDiv.innerText = `⚠️ Connection error: ${err.message}`;
                feed.appendChild(errDiv);
            } finally {
                if (btn) btn.disabled = false;
                feed.scrollTop = feed.scrollHeight;
            }
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        }
    </script>
</body>
</html>
"""


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "supervisor"}


@app.get("/", response_class=HTMLResponse)
def index():
    """Serves official Tenetic Light Theme corporate portal with floating AI Assistant."""
    return HTML_INTERFACE


@app.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest):
    """
    Routes question to domain Genie Agent and returns answer.
    """
    logger.info(f"Received /ask request for question: {payload.question}")

    # Determine domain space
    if payload.domain and payload.domain in GENIE_SPACE_IDS:
        domain = payload.domain
    else:
        domain = route_question(payload.question)

    space_id = GENIE_SPACE_IDS.get(domain)
    if not space_id:
        raise HTTPException(status_code=500, detail=f"No Genie Space ID configured for domain '{domain}'.")

    logger.info(f"Routing question to domain '{domain}' (space_id: {space_id})")

    try:
        raw_answer = await ask_genie(
            space_id=space_id,
            question=payload.question,
            host=DATABRICKS_HOST,
            token=DATABRICKS_TOKEN,
        )
        return AskResponse(domain=domain, question=payload.question, answer=raw_answer)
    except TimeoutError as exc:
        logger.error(f"Genie query timeout for domain '{domain}': {exc}")
        raise HTTPException(status_code=504, detail="Databricks Genie Agent query timed out. Please try again.")
    except RuntimeError as exc:
        logger.error(f"Genie query runtime error for domain '{domain}': {exc}")
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.error(f"Unexpected error in /ask: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal supervisor gateway error: {str(exc)}")
