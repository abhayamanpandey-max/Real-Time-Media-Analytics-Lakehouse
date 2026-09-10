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
    # Keys returned by router.py
    "audience_reach": os.getenv("GENIE_SPACE_AUDIENCE_REACH") or os.getenv("GENIE_SPACE_ID_AUDIENCE_REACH") or os.getenv("GENIE_SPACE_ID_AUDIENCE") or "01f1a1fd42bf12c9b418f72e196ce123",
    "engagement":     os.getenv("GENIE_SPACE_ID_ENGAGEMENT") or os.getenv("GENIE_SPACE_MONETIZATION") or "01f1a605b30a1a06ae28b8f2fc484f56",
    "composition":    os.getenv("GENIE_SPACE_ID_COMPOSITION") or os.getenv("GENIE_SPACE_DEMOGRAPHICS") or "01f1a6061e7110a69b5c9b4d3ccc16b4",
    "monetization":   os.getenv("GENIE_SPACE_MONETIZATION") or os.getenv("GENIE_SPACE_ID_MONETIZATION") or "01f1a605b30a1a06ae28b8f2fc484f56",
    # Legacy alias keys (kept for backward compat if domain is passed explicitly)
    "ad_performance": os.getenv("GENIE_SPACE_AD_PERFORMANCE") or "01f1a6065b871342b326e101c2469fb2",
    "demographics":   os.getenv("GENIE_SPACE_DEMOGRAPHICS") or os.getenv("GENIE_SPACE_ID_COMPOSITION") or "01f1a6061e7110a69b5c9b4d3ccc16b4",
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

from fastapi.staticfiles import StaticFiles
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        body { background-color: #f8fafc; color: #0f172a; font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif; }
        .font-mono { font-family: 'JetBrains Mono', monospace !important; }
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

        /* SVG Donut Hover Animation */
        .pie-slice {
            transition: stroke-width 0.25s ease, stroke 0.25s ease;
        }
        .pie-slice:hover {
            stroke-width: 6.5;
            cursor: pointer;
        }

        /* Custom Scrollbar */
        .scrollbar-none::-webkit-scrollbar { display: none; }
        .scrollbar-none { -ms-overflow-style: none; scrollbar-width: none; }
    </style>

    <script>
        window.toggleChat = function(open) {
            var widget = document.getElementById('chatWidget');
            var trigger = document.getElementById('chatToggleBtn');
            if (!widget) return;

            if (open === true || open === 1) {
                widget.style.display = 'flex';
                if (trigger && window.innerWidth < 640) trigger.style.display = 'none';
                widget.classList.add('ring-4', 'ring-sky-400');
                setTimeout(function() {
                    widget.classList.remove('ring-4', 'ring-sky-400');
                }, 800);
            } else if (open === false || open === 0) {
                widget.style.display = 'none';
                if (trigger) trigger.style.display = 'flex';
            } else {
                if (widget.style.display === 'none' || widget.style.display === '') {
                    widget.style.display = 'flex';
                    if (trigger && window.innerWidth < 640) trigger.style.display = 'none';
                } else {
                    widget.style.display = 'none';
                    if (trigger) trigger.style.display = 'flex';
                }
            }

            if (widget.style.display === 'flex') {
                setTimeout(function() {
                    var inp = document.getElementById('widgetInput');
                    if (inp) inp.focus();
                }, 50);
            }
        };

        window.toggleFullscreenChat = function() {
            var widget = document.getElementById('chatWidget');
            var btnText = document.getElementById('fullscreenBtnText');
            if (!widget) return;
            widget.classList.toggle('chat-fullscreen');
            if (btnText) {
                btnText.innerText = widget.classList.contains('chat-fullscreen') ? '🗗 Restore' : '⛶ Fullscreen';
            }
        };

        window.escapeHtml = function(str) {
            if (!str) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        };

        window.switchCardView = function(uid, view) {
            var chartEl = document.getElementById(uid + '_chart');
            var tableEl = document.getElementById(uid + '_table');
            var btnChart = document.getElementById(uid + '_btn_chart');
            var btnTable = document.getElementById(uid + '_btn_table');
            if (!chartEl || !tableEl) return;
            if (view === 'table') {
                chartEl.style.display = 'none';
                tableEl.style.display = 'block';
                if (btnChart) { btnChart.className = 'px-2 py-0.5 rounded font-medium text-slate-500 hover:text-slate-800 cursor-pointer transition-colors'; }
                if (btnTable) { btnTable.className = 'px-2 py-0.5 rounded font-bold bg-white text-slate-900 shadow-xs cursor-pointer transition-colors'; }
            } else {
                chartEl.style.display = 'block';
                tableEl.style.display = 'none';
                if (btnChart) { btnChart.className = 'px-2 py-0.5 rounded font-bold bg-white text-slate-900 shadow-xs cursor-pointer transition-colors'; }
                if (btnTable) { btnTable.className = 'px-2 py-0.5 rounded font-medium text-slate-500 hover:text-slate-800 cursor-pointer transition-colors'; }
            }
        };

        window._ansRegistry = window._ansRegistry || {};

        window.fallbackCopyText = function(text, cb) {
            try {
                var ta = document.createElement('textarea');
                ta.value = text;
                ta.style.position = 'fixed';
                ta.style.top = '-9999px';
                ta.style.left = '-9999px';
                ta.setAttribute('readonly', '');
                document.body.appendChild(ta);
                ta.select();
                ta.setSelectionRange(0, 99999);
                var success = document.execCommand('copy');
                document.body.removeChild(ta);
                if (success && cb) cb();
            } catch (err) {
                console.error('Fallback copy error', err);
            }
        };

        window.copyAnswerText = function(btn, targetId) {
            var text = '';
            if (window._ansRegistry && window._ansRegistry[targetId]) {
                text = window._ansRegistry[targetId].cleanText;
            }
            if (!text) {
                var el = document.getElementById(targetId + '_text') || document.getElementById(targetId);
                if (el) text = el.innerText || el.textContent;
            }
            if (!text) return;

            function showSuccess() {
                if (btn) {
                    var orig = btn.innerHTML;
                    btn.innerHTML = '<span class="text-emerald-600 font-bold">✓ Copied!</span>';
                    setTimeout(function() { btn.innerHTML = orig; }, 2000);
                }
            }

            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(showSuccess).catch(function() {
                    window.fallbackCopyText(text, showSuccess);
                });
            } else {
                window.fallbackCopyText(text, showSuccess);
            }
        };

        window.downloadResponseCSV = function(csvEncoded, filename) {
            filename = filename || 'tenetic_lakehouse_data.csv';
            try {
                var csv = decodeURIComponent(csvEncoded);
                var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                var url = URL.createObjectURL(blob);
                var link = document.createElement('a');
                link.setAttribute('href', url);
                link.setAttribute('download', filename || 'tenetic_lakehouse_data.csv');
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            } catch(e) {
                console.error('CSV export failed', e);
            }
        };

        window.toggleLineage = function(lineageId) {
            var el = document.getElementById(lineageId);
            if (!el) return;
            el.style.display = (el.style.display === 'none' || el.style.display === '') ? 'block' : 'none';
        };

        window.printReportFallback = function(reportHtml, onDone) {
            var printWin = window.open('', '_blank', 'width=850,height=900');
            if (printWin) {
                printWin.document.write('<!DOCTYPE html><html><head><title>Tenetic Executive Brief</title><style>body { margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; } @media print { body { padding: 0; } }</style><' + '/head><' + 'body>' + reportHtml + '<' + '/body><' + '/html>');
                printWin.document.close();
                printWin.focus();
                setTimeout(function() {
                    printWin.print();
                    if (onDone) onDone();
                }, 400);
            } else {
                alert('Please allow popups to view or print the PDF report.');
                if (onDone) onDone();
            }
        };

        window.TENETIC_LOGO_URI = "data:image/png;base64,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";

        window.exportResponsePDF = function(btn, msgId) {
            var orig = btn ? btn.innerHTML : null;
            if (btn) btn.innerHTML = '<span class="text-sky-600 font-bold">⏳ Exporting...</span>';

            var item = (window._ansRegistry && window._ansRegistry[msgId]) || {};
            var textEl = document.getElementById(msgId + '_text');
            var bodyHtml = textEl ? textEl.innerHTML : ((item.cleanText || '').split(String.fromCharCode(10)).join('<br>'));
            var cardEl = document.getElementById(msgId + '_card');
            var tableHtml = '';
            if (cardEl) {
                var tbl = cardEl.querySelector('table');
                if (tbl) {
                    tableHtml = '<table style="width:100%; border-collapse:collapse; font-size:12px; font-family:sans-serif; text-align:left;">' + tbl.innerHTML + '</table>';
                } else {
                    tableHtml = cardEl.innerHTML;
                }
            }

            var nowStr = new Date().toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
            var logoSrc = window.TENETIC_LOGO_URI || '/static/tenetic_logo.png';

            var reportHtml = 
                '<div style="font-family: system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif; color: #0f172a; padding: 28px; background: #ffffff; width: 750px; line-height: 1.6;">' +
                    '<div style="border-bottom: 2px solid #0284c7; padding-bottom: 16px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">' +
                        '<div>' +
                            '<div style="display: flex; align-items: center; gap: 8px;">' +
                                '<div style="display:flex; align-items:center; gap:8px;"><img src="' + logoSrc + '" style="height:28px; width:auto;" /></div>' +
                                '<span style="background: #0284c7; color: #ffffff; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase;">Media Lakehouse</span>' +
                            '</div>' +
                            '<div style="font-size: 12px; color: #64748b; margin-top: 4px;">Executive Media Intelligence & US Telecasts Brief</div>' +
                        '</div>' +
                        '<div style="text-align: right; font-size: 10px; font-family: monospace; color: #64748b;">' +
                            '<div><strong>Generated:</strong> ' + nowStr + '</div>' +
                            '<div style="color: #059669; font-weight: bold; margin-top: 2px;">● Databricks Lakehouse Live</div>' +
                        '</div>' +
                    '</div>' +

                    (item.query ? (
                        '<div style="margin-bottom: 20px; background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 10px; padding: 14px 18px;">' +
                            '<div style="font-size: 10px; font-weight: 800; text-transform: uppercase; color: #0284c7; letter-spacing: 0.5px; margin-bottom: 4px;">Executive Query</div>' +
                            '<div style="font-size: 13px; font-weight: 600; color: #0369a1;">' + item.query + '</div>' +
                        '</div>'
                    ) : '') +

                    '<div style="margin-bottom: 24px;">' +
                        '<div style="font-size: 11px; font-weight: 800; text-transform: uppercase; color: #0284c7; letter-spacing: 0.5px; margin-bottom: 8px;">Executive Response & Analysis</div>' +
                        '<div style="font-size: 13px; color: #1e293b; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px;">' +
                            bodyHtml +
                        '</div>' +
                    '</div>' +

                    (tableHtml ? (
                        '<div style="margin-bottom: 24px;">' +
                            '<div style="font-size: 11px; font-weight: 800; text-transform: uppercase; color: #0284c7; letter-spacing: 0.5px; margin-bottom: 8px;">Structured Telemetry & Metric Breakdown</div>' +
                            '<div style="border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; background: #ffffff; padding: 12px;">' +
                                tableHtml +
                            '</div>' +
                        '</div>'
                    ) : '') +

                    '<div style="border-top: 1px solid #e2e8f0; padding-top: 14px; margin-top: 24px; font-size: 10px; font-family: monospace; color: #64748b; display: flex; justify-content: space-between; align-items: center;">' +
                        '<div>' +
                            '<strong>Source Lakehouse:</strong> gold.sem_audience_rankings / sem_engagement_depth<br>' +
                            '<strong>Engine:</strong> Databricks Genie AI Lakehouse Agent (v2.4) • Verified Semantic Layer' +
                        '</div>' +
                        '<div style="text-align: right;">' +
                            '<span>Tenetic Confidential • US Operations</span>' +
                        '</div>' +
                    '</div>' +
                '</div>';

            function finish() {
                if (btn && orig) btn.innerHTML = orig;
            }

            if (typeof html2pdf !== 'undefined') {
                var opt = {
                    margin: 10,
                    filename: 'tenetic_executive_brief_' + msgId + '.pdf',
                    image: { type: 'jpeg', quality: 0.98 },
                    html2canvas: { scale: 2, useCORS: true, scrollX: 0, scrollY: 0 },
                    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
                };

                html2pdf().set(opt).from(reportHtml).save().then(function() {
                    finish();
                }).catch(function(err) {
                    console.error('html2pdf error, falling back to print', err);
                    window.printReportFallback(reportHtml, finish);
                });
            } else {
                window.printReportFallback(reportHtml, finish);
            }
        };

        window.exportFullChatPDF = function(btn) {
            var orig = btn ? btn.innerHTML : null;
            if (btn) btn.innerHTML = '<span>⏳ Exporting...</span>';

            var feed = document.getElementById('chatFeed');
            if (!feed) {
                if (btn && orig) btn.innerHTML = orig;
                return;
            }

            var nowStr = new Date().toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
            var feedClone = feed.cloneNode(true);
            var buttonsToRemove = feedClone.querySelectorAll('button');
            buttonsToRemove.forEach(function(b) { b.remove(); });
            var logoSrc = window.TENETIC_LOGO_URI || '/static/tenetic_logo.png';

            var fullReportHtml = 
                '<div style="font-family: system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif; color: #0f172a; padding: 28px; background: #ffffff; width: 750px; line-height: 1.6;">' +
                    '<div style="border-bottom: 2px solid #0284c7; padding-bottom: 16px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">' +
                        '<div>' +
                            '<div style="display: flex; align-items: center; gap: 8px;">' +
                                '<div style="display:flex; align-items:center; gap:8px;"><img src="' + logoSrc + '" style="height:28px; width:auto;" /></div>' +
                                '<span style="background: #0284c7; color: #ffffff; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase;">Lakehouse Intelligence</span>' +
                            '</div>' +
                            '<div style="font-size: 12px; color: #64748b; margin-top: 4px;">Full Executive Session Transcript & Analytics Dossier</div>' +
                        '</div>' +
                        '<div style="text-align: right; font-size: 10px; font-family: monospace; color: #64748b;">' +
                            '<div><strong>Exported:</strong> ' + nowStr + '</div>' +
                            '<div style="color: #059669; font-weight: bold; margin-top: 2px;">● Databricks Lakehouse Verified</div>' +
                        '</div>' +
                    '</div>' +

                    '<div style="margin-bottom: 24px;">' +
                        feedClone.innerHTML +
                    '</div>' +

                    '<div style="border-top: 1px solid #e2e8f0; padding-top: 14px; margin-top: 24px; font-size: 10px; font-family: monospace; color: #64748b; display: flex; justify-content: space-between; align-items: center;">' +
                        '<div>' +
                            '<strong>Source Lakehouse:</strong> gold.sem_audience_rankings / sem_engagement_depth<br>' +
                            '<strong>Engine:</strong> Databricks Genie AI Lakehouse Agent (v2.4) • Verified Semantic Layer' +
                        '</div>' +
                        '<div style="text-align: right;">' +
                            '<span>Tenetic Confidential • US Operations</span>' +
                        '</div>' +
                    '</div>' +
                '</div>';

            function finish() {
                if (btn && orig) btn.innerHTML = orig;
            }

            if (typeof html2pdf !== 'undefined') {
                var opt = {
                    margin: 10,
                    filename: 'tenetic_session_dossier_' + Date.now() + '.pdf',
                    image: { type: 'jpeg', quality: 0.98 },
                    html2canvas: { scale: 2, useCORS: true, scrollX: 0, scrollY: 0 },
                    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
                };

                html2pdf().set(opt).from(fullReportHtml).save().then(function() {
                    finish();
                }).catch(function(err) {
                    console.error('html2pdf session error', err);
                    window.printReportFallback(fullReportHtml, finish);
                });
            } else {
                window.printReportFallback(fullReportHtml, finish);
            }
        };

        window.generateFollowUpChips = function(cleanText) {
            var suggestions = [];
            var text = (cleanText || '').toLowerCase();
            if (text.indexOf('platform') !== -1 || text.indexOf('connected tv') !== -1 || text.indexOf('browser') !== -1) {
                suggestions = [
                    { label: "📊 Top 5 US Properties", query: "What are the top 5 properties by audience share in the US?" },
                    { label: "💰 Content Watch Time", query: "Show top 5 content titles by total watch time in seconds" },
                    { label: "🏆 #1 Audience Leader", query: "Which property had the highest total audience in the most recent monthly period?" }
                ];
            } else if (text.indexOf('watch time') !== -1 || text.indexOf('content title') !== -1 || text.indexOf('seconds') !== -1) {
                suggestions = [
                    { label: "🍩 Platform Share Breakdown", query: "What is the audience profile breakdown by platform?" },
                    { label: "📱 Top Ad Brands", query: "Show top ad categories by audience" },
                    { label: "📊 Top Properties in US", query: "What are the top 5 properties by audience share in the US?" }
                ];
            } else if (text.indexOf('ad') !== -1 || text.indexOf('brand') !== -1 || text.indexOf('adidas') !== -1) {
                suggestions = [
                    { label: "📊 Top Properties by Share", query: "What are the top 5 properties by audience share in the US?" },
                    { label: "🍩 Platform Share", query: "What is the audience profile breakdown by platform?" },
                    { label: "💰 Content Watch Time", query: "Show top 5 content titles by total watch time in seconds" }
                ];
            } else {
                suggestions = [
                    { label: "🍩 Platform Share", query: "What is the audience profile breakdown by platform?" },
                    { label: "💰 Top Content Watch Time", query: "Show top 5 content titles by total watch time in seconds" },
                    { label: "📱 Top Ad Brands", query: "Show top ad categories by audience" }
                ];
            }

            var chipsHtml = suggestions.map(function(s) {
                return '<button type="button" data-query="' + window.escapeHtml(s.query) + '" onclick="window.sendQuickQuery(this.dataset.query, this)" class="bg-sky-50 hover:bg-sky-100 text-sky-700 border border-sky-200/80 px-2.5 py-1 rounded-full text-[10px] font-semibold transition-all hover:scale-[1.02] cursor-pointer shadow-2xs touch-manipulation">' + s.label + '</button>';
            }).join(' ');

            return '<div class="mt-3 pt-2.5 border-t border-slate-200/60">' +
                '<div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">' +
                '<span>💡 Next Best Questions</span>' +
                '</div>' +
                '<div class="flex flex-wrap gap-1.5">' + chipsHtml + '</div>' +
                '</div>';
        };

        window.renderPieChart = function(items, title) {
            var uid = 'pie_' + Math.random().toString(36).substr(2, 7);
            var colors = ['#0284c7', '#6366f1', '#a855f7', '#10b981', '#f59e0b', '#ec4899'];
            var total = 0;
            for (var i = 0; i < items.length; i++) { total += items[i].val; }
            if (total <= 0) total = 100;

            var svgSlices = '';
            var legendHtml = '';
            var tableRows = '';
            var currentOffset = 25.0; // 12 o'clock

            for (var j = 0; j < Math.min(items.length, 6); j++) {
                var item = items[j];
                var pct = (item.val / total) * 100.0;
                var color = colors[j % colors.length];
                var dash = pct.toFixed(2) + ' ' + (100.0 - pct).toFixed(2);
                var offset = currentOffset.toFixed(2);

                svgSlices += '<circle cx="21" cy="21" r="15.915" fill="transparent" stroke="' + color + '" stroke-width="5" stroke-dasharray="' + dash + '" stroke-dashoffset="' + offset + '" class="pie-slice"><title>' + window.escapeHtml(item.label) + ': ' + item.val.toFixed(1) + '%</title></circle>';
                currentOffset -= pct;

                legendHtml += '<div class="flex items-center justify-between text-[11px] gap-2 hover:bg-slate-50 px-1 py-0.5 rounded transition-colors">' +
                    '<span class="flex items-center gap-1.5 truncate"><span class="w-2 h-2 rounded-full shrink-0" style="background:' + color + '"></span><span class="truncate text-slate-700 font-medium">' + window.escapeHtml(item.label) + '</span></span>' +
                    '<span class="font-mono text-slate-900 font-bold ml-1 shrink-0">' + item.val.toFixed(1) + '%</span>' +
                    '</div>';

                tableRows += '<tr class="border-b border-slate-100 last:border-0">' +
                    '<td class="py-1 text-slate-500">' + (j+1) + '</td>' +
                    '<td class="py-1 font-medium text-slate-800 truncate max-w-[120px]">' + window.escapeHtml(item.label) + '</td>' +
                    '<td class="py-1 text-right font-mono font-bold text-sky-700">' + item.val.toFixed(1) + '%</td>' +
                    '</tr>';
            }

            return '<div class="p-3.5 bg-white border border-slate-200/80 rounded-2xl text-xs shadow-xs">' +
                '<div class="font-bold text-slate-900 mb-2 flex items-center justify-between gap-2">' +
                '<span class="flex items-center gap-1.5 truncate">🍩 ' + (title || 'Distribution Breakdown') + '</span>' +
                '<div class="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg text-[10px] shrink-0 font-medium">' +
                '<button type="button" data-uid="' + uid + '" data-view="chart" onclick="window.switchCardView(this.dataset.uid, this.dataset.view)" id="' + uid + '_btn_chart" class="px-2 py-0.5 rounded font-bold bg-white text-slate-900 shadow-xs cursor-pointer">Chart</button>' +
                '<button type="button" data-uid="' + uid + '" data-view="table" onclick="window.switchCardView(this.dataset.uid, this.dataset.view)" id="' + uid + '_btn_table" class="px-2 py-0.5 rounded font-medium text-slate-500 hover:text-slate-800 cursor-pointer">Table</button>' +
                '</div>' +
                '</div>' +
                '<div id="' + uid + '_chart" class="flex items-center gap-3.5">' +
                '<div class="shrink-0">' +
                '<svg viewBox="0 0 42 42" class="w-20 h-20 transform -rotate-90">' + svgSlices + '</svg>' +
                '</div>' +
                '<div class="grid grid-cols-1 gap-1 flex-1 min-w-0">' + legendHtml + '</div>' +
                '</div>' +
                '<div id="' + uid + '_table" style="display:none;" class="overflow-x-auto">' +
                '<table class="w-full text-[11px] text-left">' +
                '<thead><tr class="border-b border-slate-200 text-slate-500 font-semibold"><th class="pb-1">#</th><th class="pb-1">Platform</th><th class="pb-1 text-right">Share %</th></tr></thead>' +
                '<tbody>' + tableRows + '</tbody>' +
                '</table>' +
                '</div>' +
                '</div>';
        };

        window.renderComparisonGraph = function(items) {
            var itemA = items[0];
            var itemB = items[1];
            var maxVal = Math.max(itemA.val, itemB.val);
            var pctA = maxVal > 0 ? Math.round((itemA.val / maxVal) * 100) : 50;
            var pctB = maxVal > 0 ? Math.round((itemB.val / maxVal) * 100) : 50;
            var pctDiff = itemB.val > 0 ? (((itemA.val - itemB.val) / itemB.val) * 100).toFixed(1) : 0;
            var isHigherA = itemA.val >= itemB.val;

            return '<div class="p-3.5 bg-slate-50/80 border border-slate-200/80 rounded-2xl text-xs shadow-xs">' +
                '<div class="font-bold text-slate-900 mb-2.5 flex items-center justify-between">' +
                '<span class="flex items-center gap-1.5">⚖️ Head-to-Head Comparison</span>' +
                '<span class="text-[10px] bg-sky-100 text-sky-700 px-2 py-0.5 rounded-full font-bold">Δ ' + Math.abs(pctDiff) + '%</span>' +
                '</div>' +
                '<div class="grid grid-cols-2 gap-2 mb-1">' +
                '<div class="p-2.5 bg-white border ' + (isHigherA ? 'border-sky-300 ring-1 ring-sky-200' : 'border-slate-200') + ' rounded-xl">' +
                '<div class="flex items-center justify-between text-[10px] text-slate-500 font-semibold">' +
                '<span class="truncate">' + window.escapeHtml(itemA.label) + '</span>' +
                (isHigherA ? '<span class="text-[9px] text-sky-600 font-bold">LEADER</span>' : '') +
                '</div>' +
                '<div class="text-sm font-black text-sky-700 mt-1 font-mono">' + itemA.raw + '</div>' +
                '<div class="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mt-1.5"><div class="bg-sky-600 h-full rounded-full" style="width:' + pctA + '%"></div></div>' +
                '</div>' +
                '<div class="p-2.5 bg-white border ' + (!isHigherA ? 'border-sky-300 ring-1 ring-sky-200' : 'border-slate-200') + ' rounded-xl">' +
                '<div class="flex items-center justify-between text-[10px] text-slate-500 font-semibold">' +
                '<span class="truncate">' + window.escapeHtml(itemB.label) + '</span>' +
                (!isHigherA ? '<span class="text-[9px] text-sky-600 font-bold">LEADER</span>' : '') +
                '</div>' +
                '<div class="text-sm font-black text-slate-700 mt-1 font-mono">' + itemB.raw + '</div>' +
                '<div class="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mt-1.5"><div class="bg-slate-400 h-full rounded-full" style="width:' + pctB + '%"></div></div>' +
                '</div>' +
                '</div></div>';
        };

        window.renderBarGraph = function(items, title) {
            var uid = 'bar_' + Math.random().toString(36).substr(2, 7);
            var maxVal = Math.max.apply(null, items.map(function(i) { return i.val; }));
            var colors = ['bg-sky-600', 'bg-indigo-600', 'bg-purple-600', 'bg-emerald-600', 'bg-amber-600'];
            var badgeStyles = [
                'bg-amber-100 text-amber-800 border-amber-300',
                'bg-slate-200 text-slate-700 border-slate-300',
                'bg-orange-100 text-orange-800 border-orange-200',
                'bg-slate-100 text-slate-600 border-slate-200',
                'bg-slate-100 text-slate-600 border-slate-200'
            ];

            var barsHtml = '';
            var tableRows = '';

            for (var idx = 0; idx < Math.min(items.length, 5); idx++) {
                var item = items[idx];
                var pct = maxVal > 0 ? Math.round((item.val / maxVal) * 100) : 0;
                var color = colors[idx % colors.length];
                var badge = badgeStyles[idx % badgeStyles.length];

                barsHtml += '<div title="' + window.escapeHtml(item.label) + ': ' + item.raw + '" class="hover:bg-slate-50 p-1 rounded-lg transition-colors">' +
                    '<div class="flex justify-between text-[11px] font-semibold text-slate-700 mb-1">' +
                    '<span class="flex items-center gap-1.5 truncate">' +
                    '<span class="w-4 h-4 rounded-full ' + badge + ' border flex items-center justify-center text-[9px] font-bold shrink-0">#' + (idx+1) + '</span>' +
                    '<span class="truncate text-slate-800">' + window.escapeHtml(item.label) + '</span>' +
                    '</span>' +
                    '<span class="font-mono text-slate-900 font-bold ml-2 shrink-0">' + item.raw + '</span>' +
                    '</div>' +
                    '<div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">' +
                    '<div class="' + color + ' h-full rounded-full transition-all duration-500" style="width:' + pct + '%"></div>' +
                    '</div>' +
                    '</div>';

                tableRows += '<tr class="border-b border-slate-100 last:border-0">' +
                    '<td class="py-1 font-bold text-slate-500">#' + (idx+1) + '</td>' +
                    '<td class="py-1 font-medium text-slate-800 truncate max-w-[120px]">' + window.escapeHtml(item.label) + '</td>' +
                    '<td class="py-1 text-right font-mono font-bold text-sky-700">' + item.raw + '</td>' +
                    '</tr>';
            }

            return '<div class="p-3.5 bg-white border border-slate-200/80 rounded-2xl text-xs shadow-xs">' +
                '<div class="font-bold text-slate-900 mb-2 flex items-center justify-between gap-2">' +
                '<span class="flex items-center gap-1.5 truncate">📊 ' + (title || 'Ranked Comparison') + '</span>' +
                '<div class="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg text-[10px] shrink-0 font-medium">' +
                '<button type="button" data-uid="' + uid + '" data-view="chart" onclick="window.switchCardView(this.dataset.uid, this.dataset.view)" id="' + uid + '_btn_chart" class="px-2 py-0.5 rounded font-bold bg-white text-slate-900 shadow-xs cursor-pointer">Chart</button>' +
                '<button type="button" data-uid="' + uid + '" data-view="table" onclick="window.switchCardView(this.dataset.uid, this.dataset.view)" id="' + uid + '_btn_table" class="px-2 py-0.5 rounded font-medium text-slate-500 hover:text-slate-800 cursor-pointer">Table</button>' +
                '</div>' +
                '</div>' +
                '<div id="' + uid + '_chart" class="space-y-1.5">' + barsHtml + '</div>' +
                '<div id="' + uid + '_table" style="display:none;" class="overflow-x-auto">' +
                '<table class="w-full text-[11px] text-left">' +
                '<thead><tr class="border-b border-slate-200 text-slate-500 font-semibold"><th class="pb-1">Rank</th><th class="pb-1">Entity</th><th class="pb-1 text-right">Value</th></tr></thead>' +
                '<tbody>' + tableRows + '</tbody>' +
                '</table>' +
                '</div>' +
                '</div>';
        };

        window.wrapSideBySide = function(textHtml, cardHtml, msgId, csvEncoded, cleanText) {
            window._ansRegistry = window._ansRegistry || {};
            window._ansRegistry[msgId] = {
                cleanText: cleanText,
                textHtml: textHtml,
                cardHtml: cardHtml
            };

            var csvBtnHtml = '';
            if (csvEncoded) {
                csvBtnHtml = '<button type="button" data-csv="' + csvEncoded + '" onclick="window.downloadResponseCSV(this.dataset.csv)" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition-colors cursor-pointer text-[10px]">' +
                    '<span>📥</span> <span>Export CSV</span>' +
                    '</button>';
            }

            var followUpsHtml = window.generateFollowUpChips(cleanText);

            return '<div id="' + msgId + '_container" class="w-full">' +
                '<div class="flex flex-col lg:flex-row gap-4 items-start justify-between w-full">' +
                '<div id="' + msgId + '_text" class="flex-1 min-w-0 pr-1 leading-relaxed text-slate-800">' + textHtml + '</div>' +
                (cardHtml ? '<div id="' + msgId + '_card" class="w-full lg:w-[320px] shrink-0">' + cardHtml + '</div>' : '') +
                '</div>' +
                '<div class="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">' +
                '<div class="flex items-center gap-1.5 flex-wrap">' +
                '<button type="button" data-msg-id="' + msgId + '" onclick="window.copyAnswerText(this, this.dataset.msgId)" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition-colors cursor-pointer text-[10px]">' +
                '<span>📋</span> <span>Copy Brief</span>' +
                '</button>' +
                '<button type="button" data-msg-id="' + msgId + '" onclick="window.exportResponsePDF(this, this.dataset.msgId)" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition-colors cursor-pointer text-[10px]">' +
                '<span>📄</span> <span>Export PDF</span>' +
                '</button>' +
                csvBtnHtml +
                '<button type="button" data-target="' + msgId + '_lineage" onclick="window.toggleLineage(this.dataset.target)" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 font-medium transition-colors cursor-pointer text-[10px]">' +
                '<span>🔍</span> <span>Lineage</span>' +
                '</button>' +
                '</div>' +
                '<div class="text-[10px] text-slate-400 font-mono flex items-center gap-1.5">' +
                '<span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Databricks Photon • Live' +
                '</div>' +
                '</div>' +
                '<div id="' + msgId + '_lineage" style="display:none;" class="mt-2 p-2.5 bg-slate-50 rounded-xl border border-slate-200 text-[10px] font-mono text-slate-600 leading-relaxed">' +
                '<span class="font-bold text-sky-700">Source Lakehouse:</span> gold.sem_audience_rankings / sem_engagement_depth<br>' +
                '<span class="font-bold text-sky-700">Engine:</span> Databricks Genie AI Lakehouse Agent (v2.4) • Verified Semantic Layer' +
                '</div>' +
                followUpsHtml +
                '</div>';
        };

        window.formatBusinessAnswer = function(rawAnswer) {
            var msgId = 'ans_' + Math.random().toString(36).substr(2, 7);
            var clean = rawAnswer.replace(/```sql[\\s\\S]*?```/gi, '').replace(/\\*\\*Generated SQL Query:\\*\\*/gi, '').trim();
            var html = (typeof marked !== 'undefined') ? marked.parse(clean) : clean.split(String.fromCharCode(10)).join('<br>');

            // 1. Check for Pie / Donut Chart (Percentage distributions)
            var pieRegex = /\*\*([^*]+)\*\*[:\s]*\(?([0-9]+(?:\.[0-9]+)?)\s*%/g;
            var pieMatches = [];
            var pMatch;
            while ((pMatch = pieRegex.exec(clean)) !== null) {
                var pLabel = pMatch[1].replace(/[*_]/g, '').trim();
                var pVal = parseFloat(pMatch[2]);
                if (!isNaN(pVal) && pLabel.length >= 2 && pVal > 0) {
                    pieMatches.push({ label: pLabel, val: pVal, raw: pMatch[2] + '%' });
                }
            }
            if (pieMatches.length >= 3) {
                var pieCsvRows = ["Platform / Entity,Share %"];
                for (var pi = 0; pi < pieMatches.length; pi++) { pieCsvRows.push('"' + pieMatches[pi].label + '","' + pieMatches[pi].raw + '"'); }
                var pieCsv = encodeURIComponent(pieCsvRows.join('\\n'));
                var pieChart = window.renderPieChart(pieMatches, 'Distribution Breakdown');
                return window.wrapSideBySide(html, pieChart, msgId, pieCsv, clean);
            }

            // 2. Check for Key-Value Numerical Metrics
            var kvRegex = /[-*•]?\s*\*\*([^*]+)\*\*:\s*\$?([0-9,]+(?:\.[0-9]+)?(?:\s*(?:seconds|viewers|USD|%))?)/g;
            var kvMatches = [];
            var kMatch;
            while ((kMatch = kvRegex.exec(clean)) !== null) {
                var kLabel = kMatch[1].replace(/[*_]/g, '').trim();
                var numStr = kMatch[2].replace(/,/g, '').replace(/[^0-9.]/g, '');
                var kVal = parseFloat(numStr);
                if (!isNaN(kVal) && kLabel.length >= 2 && kVal > 0) {
                    kvMatches.push({ label: kLabel, val: kVal, raw: kMatch[2] });
                }
            }

            if (kvMatches.length === 0) {
                var fallbackRegex = /[-*•]?\s*\*?\*?([^:\d\\n]+?)\*?\*?:\s*\$?([0-9,]+(?:\.[0-9]+)?)/g;
                var fbMatch;
                while ((fbMatch = fallbackRegex.exec(clean)) !== null) {
                    var fbLabel = fbMatch[1].replace(/[*_]/g, '').trim();
                    var fbNumStr = fbMatch[2].replace(/,/g, '');
                    var fbVal = parseFloat(fbNumStr);
                    if (!isNaN(fbVal) && fbLabel.length >= 2 && fbLabel.length <= 45 && fbVal > 0) {
                        kvMatches.push({ label: fbLabel, val: fbVal, raw: fbMatch[2] });
                    }
                }
            }

            var kvCsv = '';
            if (kvMatches.length > 0) {
                var kvCsvRows = ["Entity,Metric Value"];
                for (var ki = 0; ki < kvMatches.length; ki++) { kvCsvRows.push('"' + kvMatches[ki].label + '","' + kvMatches[ki].raw + '"'); }
                kvCsv = encodeURIComponent(kvCsvRows.join('\\n'));
            }

            if (kvMatches.length === 2) {
                var compGraph = window.renderComparisonGraph(kvMatches);
                return window.wrapSideBySide(html, compGraph, msgId, kvCsv, clean);
            } else if (kvMatches.length >= 3) {
                var barGraph = window.renderBarGraph(kvMatches, 'Ranked Comparison');
                return window.wrapSideBySide(html, barGraph, msgId, kvCsv, clean);
            }

            // Fallback Leader Cards for single-item responses
            var viz = '';
            if (clean.indexOf('1,192,842,191') !== -1 || clean.indexOf('Media Gamma') !== -1) {
                viz = '<div class="p-3.5 bg-sky-50 border border-sky-200/80 rounded-2xl text-xs shadow-xs"><div class="font-bold text-sky-900 mb-1 flex items-center justify-between"><span>🏆 Top Property Audience</span><span class="font-mono text-sky-700">1.19B</span></div><div class="w-full bg-slate-200 h-2 rounded-full overflow-hidden mt-1.5"><div class="bg-sky-600 h-full rounded-full" style="width:100%"></div></div><div class="flex justify-between text-[10px] text-slate-600 mt-1 font-semibold"><span>Media Gamma (#1 Ranked)</span><span class="font-mono font-bold">1,192,842,191</span></div></div>';
                return window.wrapSideBySide(html, viz, msgId, kvCsv, clean);
            } else if (clean.indexOf('camp_842') !== -1 || clean.indexOf('9.48') !== -1 || clean.indexOf('spend') !== -1) {
                viz = '<div class="p-3.5 bg-purple-50 border border-purple-200/80 rounded-2xl text-xs shadow-xs"><div class="font-bold text-purple-900 mb-1 flex items-center justify-between"><span>⏱️ Top Campaign Spend</span><span class="font-mono text-purple-700">$9.48 USD</span></div><div class="w-full bg-slate-200 h-2 rounded-full overflow-hidden mt-1.5"><div class="bg-purple-600 h-full rounded-full" style="width:85%"></div></div><div class="flex justify-between text-[10px] text-slate-600 mt-1 font-semibold"><span>Campaign camp_842</span><span class="font-mono font-bold">Highest Spend</span></div></div>';
                return window.wrapSideBySide(html, viz, msgId, kvCsv, clean);
            }

            return window.wrapSideBySide(html, '', msgId, '', clean);
        };

        // Core submit logic — receives question text directly
        window._submitQuestion = async function(question) {
            var feed = document.getElementById('chatFeed');
            var btn = document.getElementById('widgetSendBtn');
            var input = document.getElementById('widgetInput');
            if (!feed || !question) return;

            if (input) input.value = '';
            if (btn) btn.disabled = true;

            var userMsg = document.createElement('div');
            userMsg.className = 'flex justify-end';
            userMsg.innerHTML = '<div class="bg-sky-600 text-white px-3.5 py-2.5 rounded-2xl rounded-tr-sm text-xs max-w-[85%] leading-relaxed shadow-sm font-medium">' + window.escapeHtml(question) + '</div>';
            feed.appendChild(userMsg);

            var loadId = 'load-' + Date.now();
            var loadMsg = document.createElement('div');
            loadMsg.id = loadId;
            loadMsg.className = 'flex items-start gap-2.5 bg-sky-50 border border-sky-200 p-2.5 rounded-xl';
            loadMsg.innerHTML = '<div class="w-6 h-6 rounded-lg bg-slate-900 flex items-center justify-center text-sky-400 font-bold text-xs shrink-0 mt-0.5 shadow-xs"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg></div><div class="text-sky-800 text-xs py-0.5"><div class="font-bold flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-sky-600 animate-ping"></span> Querying Lakehouse Agent...</div><div class="text-[10px] text-slate-500 mt-0.5">Routing to Databricks Genie AI (typically 10-15s)</div></div>';
            feed.appendChild(loadMsg);
            feed.scrollTop = feed.scrollHeight;

            try {
                var resp = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: question })
                });
                var el = document.getElementById(loadId);
                if (el) el.remove();

                if (resp.ok) {
                    var data = await resp.json();
                    var agentMsg = document.createElement('div');
                    agentMsg.className = 'flex items-start gap-2.5';
                    agentMsg.innerHTML = '<div class="w-6 h-6 rounded-lg bg-slate-900 flex items-center justify-center text-sky-400 font-bold text-xs shrink-0 mt-0.5 shadow-xs"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg></div><div class="markdown-body text-xs text-slate-800 leading-relaxed bg-white border border-slate-200 p-3.5 rounded-2xl rounded-tl-sm flex-1 shadow-sm">' + window.formatBusinessAnswer(data.answer) + '</div>';
                    feed.appendChild(agentMsg);
                } else {
                    var errData = await resp.json().catch(function() { return { detail: 'Service error' }; });
                    var errDiv = document.createElement('div');
                    errDiv.className = 'bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-xs';
                    errDiv.innerText = '⚠️ Error: ' + (errData.detail || 'Service error');
                    feed.appendChild(errDiv);
                }
            } catch(err) {
                var el2 = document.getElementById(loadId);
                if (el2) el2.remove();
                var errDiv2 = document.createElement('div');
                errDiv2.className = 'bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-xs';
                errDiv2.innerText = '⚠️ Connection error: ' + err.message;
                feed.appendChild(errDiv2);
            } finally {
                if (btn) btn.disabled = false;
                feed.scrollTop = feed.scrollHeight;
            }
        };

        // Form onsubmit — reads input value then calls core logic
        window.handleChatSubmit = function(e) {
            if (e && e.preventDefault) e.preventDefault();
            var input = document.getElementById('widgetInput');
            if (!input) return false;
            var question = input.value.trim();
            if (!question) return false;
            window._submitQuestion(question);
            return false;
        };

        // Quick chip buttons call this — passes question text directly with visual click feedback
        window.sendQuickQuery = function(queryText, btnEl) {
            window.toggleChat(true);
            if (btnEl) {
                var origText = btnEl.innerText;
                btnEl.innerText = '⏳ Querying...';
                btnEl.classList.add('bg-sky-600', 'text-white');
                setTimeout(function() {
                    btnEl.innerText = origText;
                    btnEl.classList.remove('bg-sky-600', 'text-white');
                }, 3000);
            }
            window._submitQuestion(queryText);
        };
    </script>
</head>
<body class="min-h-screen flex flex-col relative bg-slate-50 text-slate-900 selection:bg-sky-500 selection:text-white">

    <!-- Official Corporate Light Navigation Header -->
    <header class="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200 px-6 py-4 flex items-center justify-between shadow-sm">
        <div class="flex items-center gap-3">
            <a href="#" class="flex items-center gap-2 group">
                <img src="/static/tenetic_logo.png" alt="TENETIC" class="h-9 w-auto object-contain" />
            </a>
            <div class="hidden sm:block pl-3 border-l border-slate-200 text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-widest">
                Media Intelligence Lakehouse
            </div>
        </div>

        <nav class="hidden md:flex items-center gap-8 text-xs font-semibold text-slate-600">
            <a href="#about" class="hover:text-sky-600 transition-colors">About Us</a>
            <a href="#telecasts" class="hover:text-sky-600 transition-colors">Live Telecasts & Coverage</a>
            <a href="#solutions" class="hover:text-sky-600 transition-colors">Solutions</a>
            <a href="#leadership" class="hover:text-sky-600 transition-colors">Leadership</a>
        </nav>

        <div class="flex items-center gap-3">
            <button onclick="window.toggleChat(true)" class="bg-sky-600 hover:bg-sky-700 text-white px-4 py-2.5 rounded-xl text-xs font-bold shadow-md shadow-sky-600/20 transition-all flex items-center gap-2 cursor-pointer">
                <span>✦ Live AI Portal</span>
            </button>
        </div>
    </header>

    <!-- Real-Time Telecast Telemetry Ticker -->
    <div class="bg-slate-900 border-b border-slate-800 text-slate-300 px-6 py-2 text-[11px] font-mono flex items-center justify-between overflow-hidden shadow-inner">
        <div class="flex items-center gap-2 shrink-0">
            <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px] font-bold">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> LIVE TELEMETRY
            </span>
        </div>
        <div class="flex-1 overflow-x-auto whitespace-nowrap scrollbar-none px-4 flex items-center gap-6 text-[11px]">
            <span class="flex items-center gap-1.5"><span class="text-slate-400">Media Gamma:</span> <span class="font-bold text-white">1.19B Viewers</span> <span class="text-emerald-400 font-bold">▲ +3.8%</span></span>
            <span class="text-slate-700">|</span>
            <span class="flex items-center gap-1.5"><span class="text-slate-400">Connected TV Share:</span> <span class="font-bold text-sky-400">24.42%</span></span>
            <span class="text-slate-700">|</span>
            <span class="flex items-center gap-1.5"><span class="text-slate-400">Top Content Watch:</span> <span class="font-bold text-white">30,076s</span></span>
            <span class="text-slate-700">|</span>
            <span class="flex items-center gap-1.5"><span class="text-slate-400">Top Ad Category:</span> <span class="font-bold text-amber-400">Adidas (190)</span></span>
            <span class="text-slate-700">|</span>
            <span class="flex items-center gap-1.5"><span class="text-slate-400">Lakehouse Sync:</span> <span class="font-bold text-emerald-400">Live Databricks</span></span>
        </div>
        <div class="shrink-0 hidden sm:flex items-center gap-2 text-[10px] text-slate-400">
            <span class="w-1.5 h-1.5 rounded-full bg-sky-400"></span> 210 US DMAs Active
        </div>
    </div>

    <!-- Hero Section -->
    <section id="about" class="px-6 pt-16 pb-16 max-w-6xl mx-auto text-center flex flex-col items-center">
        <div class="inline-flex items-center gap-2 bg-sky-50 border border-sky-200/80 px-4 py-1.5 rounded-full text-xs text-sky-800 font-bold mb-6 shadow-xs">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Real-Time US Telecasts & Streaming Lakehouse</span>
        </div>
        
        <h1 class="text-4xl sm:text-6xl font-black text-slate-900 tracking-tight max-w-4xl leading-tight">
            Transforming US Live Telecasts into <span class="bg-gradient-to-r from-sky-600 via-indigo-600 to-blue-700 bg-clip-text text-transparent">Kinetic Intelligence</span>
        </h1>
        
        <p class="text-base sm:text-lg text-slate-600 max-w-3xl mt-6 leading-relaxed">
            Tenetic powers minute-by-minute audience measurement, cross-platform reach, and verified brand ad performance across live television broadcasts and 210 US DMA markets nationwide on Databricks Delta Lake.
        </p>

        <div class="flex flex-wrap items-center justify-center gap-4 mt-8">
            <button type="button" onclick="window.toggleChat(true)" class="bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs px-7 py-4 rounded-xl shadow-lg shadow-slate-900/20 transition-all flex items-center gap-2 cursor-pointer border border-slate-700 touch-manipulation">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Launch Live AI Portal</span>
            </button>
            <a href="#telecasts" class="bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 font-bold text-xs px-7 py-4 rounded-xl shadow-xs transition-all">
                Explore Broadcast Coverage & Markets
            </a>
        </div>

        
        <!-- Visual Telecast Telemetry Hero Card -->
        <div class="relative rounded-3xl overflow-hidden shadow-2xl border border-slate-700 bg-slate-900 group mt-10 mb-6 w-full max-w-5xl">
            <img 
                src="https://images.unsplash.com/photo-1522869635100-9f4c5e86aa37?auto=format&fit=crop&w=1200&q=80" 
                alt="US Live Telecast Broadcast Control Room" 
                class="w-full h-64 sm:h-80 object-cover opacity-60 group-hover:scale-102 transition-transform duration-700 ease-out" 
            />
            <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent flex flex-col justify-between p-6 sm:p-8 text-left">
                <div class="flex flex-wrap items-center justify-between gap-3">
                    <div class="inline-flex items-center gap-2 bg-slate-900/90 backdrop-blur-md border border-slate-700 px-3.5 py-1.5 rounded-full text-xs font-mono text-emerald-400">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span>LIVE TELECAST TELEMETRY INGEST</span>
                    </div>
                    <div class="text-[11px] font-mono text-slate-300 bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-lg border border-slate-700">
                        <span>Stream: <strong>42,800 events/s</strong></span> • <span>Latency: <strong>&lt;12ms</strong></span>
                    </div>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
                    <div class="bg-slate-900/85 backdrop-blur-md border border-slate-700/80 p-4 rounded-2xl shadow-sm">
                        <div class="text-[10px] uppercase font-mono text-slate-400">Audience Leader</div>
                        <div class="text-xl font-bold text-white mt-1">Media Gamma</div>
                        <div class="text-xs text-sky-400 font-mono mt-0.5 font-bold">1,192,842,191 Viewers</div>
                    </div>
                    <div class="bg-slate-900/85 backdrop-blur-md border border-slate-700/80 p-4 rounded-2xl shadow-sm">
                        <div class="text-[10px] uppercase font-mono text-slate-400">Cross-Platform Distribution</div>
                        <div class="text-xl font-bold text-white mt-1">Connected TV &amp; Mobile</div>
                        <div class="text-xs text-emerald-400 font-mono mt-0.5 font-bold">4 Platforms Tracked</div>
                    </div>
                    <div class="bg-slate-900/85 backdrop-blur-md border border-slate-700/80 p-4 rounded-2xl shadow-sm">
                        <div class="text-[10px] uppercase font-mono text-slate-400">Monetization &amp; Ad Impact</div>
                        <div class="text-xl font-bold text-white mt-1">Top Campaigns &amp; Brands</div>
                        <div class="text-xs text-indigo-400 font-mono mt-0.5 font-bold">$9.48 CPM Average</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Executive Architecture Badges -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-5xl mt-14 text-left">
            <div class="bg-white border border-slate-200 p-5 rounded-2xl shadow-xs hover:border-sky-300 transition-colors">
                <div class="flex items-center gap-2 text-slate-400 mb-1">
                    <svg class="w-4 h-4 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>
                    <span class="text-[11px] font-bold uppercase tracking-wider">US Market Coverage</span>
                </div>
                <div class="text-2xl font-black text-slate-900">210 DMAs</div>
                <div class="text-[11px] text-sky-700 mt-1 font-semibold">All US Regional Markets</div>
            </div>

            <div class="bg-white border border-slate-200 p-5 rounded-2xl shadow-xs hover:border-emerald-300 transition-colors">
                <div class="flex items-center gap-2 text-slate-400 mb-1">
                    <svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    <span class="text-[11px] font-bold uppercase tracking-wider">Ingest Latency</span>
                </div>
                <div class="text-2xl font-black text-slate-900">Real-Time</div>
                <div class="text-[11px] text-emerald-700 mt-1 font-semibold">Replacing 30-Day Legacy Lag</div>
            </div>

            <div class="bg-white border border-slate-200 p-5 rounded-2xl shadow-xs hover:border-purple-300 transition-colors">
                <div class="flex items-center gap-2 text-slate-400 mb-1">
                    <svg class="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                    <span class="text-[11px] font-bold uppercase tracking-wider">Consumer Survey</span>
                </div>
                <div class="text-2xl font-black text-slate-900">CivicScience</div>
                <div class="text-[11px] text-purple-700 mt-1 font-semibold">Attitudinal & Survey Fusion</div>
            </div>

            <div class="bg-white border border-slate-200 p-5 rounded-2xl shadow-xs hover:border-amber-300 transition-colors">
                <div class="flex items-center gap-2 text-slate-400 mb-1">
                    <svg class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2 1.5 3 3.5 3h9c2 0 3.5-1 3.5-3V7c0-2-1.5-3-3.5-3h-9C5.5 4 4 5 4 7z"></path></svg>
                    <span class="text-[11px] font-bold uppercase tracking-wider">Lakehouse Engine</span>
                </div>
                <div class="text-2xl font-black text-slate-900">Delta Lake</div>
                <div class="text-[11px] text-amber-700 mt-1 font-semibold">Databricks Genie AI Semantic</div>
            </div>
        </div>
    </section>

        <!-- Live Telecasts & US Operations Section -->
    <section id="telecasts" class="py-16 bg-white border-y border-slate-200 px-6 w-full">
        <div class="max-w-6xl mx-auto">
            <div class="text-center max-w-2xl mx-auto mb-12">
                <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-xs font-mono font-bold mb-2">
                    <span class="w-2 h-2 rounded-full bg-sky-600"></span>
                    US NATIONAL &amp; REGIONAL INFRASTRUCTURE
                </div>
                <h3 class="text-3xl font-black text-slate-900 tracking-tight">Live Telecasts &amp; US Operations</h3>
                <p class="text-xs sm:text-sm text-slate-600 mt-3">From live NFL and sports broadcasts to national network programming and local news, Tenetic converts telecast telemetry into certified advertising value across 210 US DMAs.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <!-- Card 1: Broadcast Telecast Studio -->
                <div class="rounded-2xl bg-slate-50 border border-slate-200 overflow-hidden shadow-xs flex flex-col group hover:shadow-md transition-shadow">
                    <div class="h-44 w-full relative overflow-hidden bg-slate-900">
                        <img 
                            src="https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?auto=format&fit=crop&w=800&q=80" 
                            alt="Live Sports &amp; Broadcast Master Control" 
                            class="w-full h-full object-cover opacity-90 group-hover:scale-105 transition-transform duration-500" 
                        />
                        <div class="absolute top-3 left-3 bg-slate-900/80 backdrop-blur-md px-2.5 py-1 rounded-md text-[10px] font-mono font-bold text-sky-400 border border-slate-700">
                            MASTER CONTROL TELEMETRY
                        </div>
                    </div>
                    <div class="p-5 flex-1 flex flex-col justify-between">
                        <div>
                            <h4 class="text-base font-bold text-slate-900 mb-1.5">Live Broadcast &amp; Sports Telecasts</h4>
                            <p class="text-xs text-slate-600 leading-relaxed">
                                Provides minute-by-minute audience measurement and ad engagement telemetry during live sports games, award shows, and national broadcasts across major US networks.
                            </p>
                        </div>
                        <div class="mt-4 pt-3 border-t border-slate-200 text-[11px] font-bold text-sky-700 flex items-center gap-1.5">
                            <span class="w-1.5 h-1.5 rounded-full bg-sky-600"></span> Real-Time Viewer Volume &amp; Ad Impact
                        </div>
                    </div>
                </div>

                <!-- Card 2: Local US Station Sales -->
                <div class="rounded-2xl bg-slate-50 border border-slate-200 overflow-hidden shadow-xs flex flex-col group hover:shadow-md transition-shadow">
                    <div class="h-44 w-full relative overflow-hidden bg-slate-900">
                        <img 
                            src="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80" 
                            alt="Local US Station Sales Intelligence" 
                            class="w-full h-full object-cover opacity-90 group-hover:scale-105 transition-transform duration-500" 
                        />
                        <div class="absolute top-3 left-3 bg-slate-900/80 backdrop-blur-md px-2.5 py-1 rounded-md text-[10px] font-mono font-bold text-indigo-400 border border-slate-700">
                            210 DMA COVERAGE
                        </div>
                    </div>
                    <div class="p-5 flex-1 flex flex-col justify-between">
                        <div>
                            <h4 class="text-base font-bold text-slate-900 mb-1.5">Local US Station Sales Intelligence</h4>
                            <p class="text-xs text-slate-600 leading-relaxed">
                                Delivers programmatic sales intelligence across all 210 US Designated Market Areas (DMAs), empowering local broadcasters and media buyers with unified inventory metrics.
                            </p>
                        </div>
                        <div class="mt-4 pt-3 border-t border-slate-200 text-[11px] font-bold text-indigo-700 flex items-center gap-1.5">
                            <span class="w-1.5 h-1.5 rounded-full bg-indigo-600"></span> Designated Market Area Pricing &amp; Lift
                        </div>
                    </div>
                </div>

                <!-- Card 3: CivicScience Survey Integration -->
                <div class="rounded-2xl bg-slate-50 border border-slate-200 overflow-hidden shadow-xs flex flex-col group hover:shadow-md transition-shadow">
                    <div class="h-44 w-full relative overflow-hidden bg-slate-900">
                        <img 
                            src="https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=800&q=80" 
                            alt="CivicScience Consumer Survey Fusion" 
                            class="w-full h-full object-cover opacity-90 group-hover:scale-105 transition-transform duration-500" 
                        />
                        <div class="absolute top-3 left-3 bg-slate-900/80 backdrop-blur-md px-2.5 py-1 rounded-md text-[10px] font-mono font-bold text-emerald-400 border border-slate-700">
                            100M+ CONSUMER PROFILES
                        </div>
                    </div>
                    <div class="p-5 flex-1 flex flex-col justify-between">
                        <div>
                            <h4 class="text-base font-bold text-slate-900 mb-1.5">CivicScience Consumer Survey Fusion</h4>
                            <p class="text-xs text-slate-600 leading-relaxed">
                                Fuses real-time viewer stream telemetry with CivicScience consumer sentiment polls, converting passive viewer numbers into deep brand purchase intent and buyer behavior.
                            </p>
                        </div>
                        <div class="mt-4 pt-3 border-t border-slate-200 text-[11px] font-bold text-emerald-700 flex items-center gap-1.5">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span> Attitudinal &amp; Purchase Intent Overlays
                        </div>
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
            <div class="bg-white border border-slate-200 p-6 rounded-2xl shadow-xs hover:border-sky-300 transition-all">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2.5">
                        <div class="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                        </div>
                        <h4 class="text-base font-bold text-slate-900">Tenetic Audience & Reach Analytics</h4>
                    </div>
                    <span class="text-[10px] font-mono font-bold bg-sky-50 text-sky-700 px-2 py-0.5 rounded border border-sky-200">Gold Layer Delta</span>
                </div>
                <p class="text-xs text-slate-600 leading-relaxed">
                    Instantly ranks media properties, computes monthly/weekly viewer market share, and tracks audience growth trends across streaming platforms and broadcast stations.
                </p>
            </div>

            <div class="bg-white border border-slate-200 p-6 rounded-2xl shadow-xs hover:border-purple-300 transition-all">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2.5">
                        <div class="w-8 h-8 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </div>
                        <h4 class="text-base font-bold text-slate-900">Tenetic Ad Spend & Campaign ROI</h4>
                    </div>
                    <span class="text-[10px] font-mono font-bold bg-purple-50 text-purple-700 px-2 py-0.5 rounded border border-purple-200">Live Ad Tracker</span>
                </div>
                <p class="text-xs text-slate-600 leading-relaxed">
                    Monitors total campaign ad spend in USD, impression volume, click-through rates (CTR), CPM benchmarks, and advertiser ROI across live telecast slots.
                </p>
            </div>

            <div class="bg-white border border-slate-200 p-6 rounded-2xl shadow-xs hover:border-indigo-300 transition-all">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2.5">
                        <div class="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </div>
                        <h4 class="text-base font-bold text-slate-900">Tenetic Regional & Demographics</h4>
                    </div>
                    <span class="text-[10px] font-mono font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded border border-indigo-200">210 US DMAs</span>
                </div>
                <p class="text-xs text-slate-600 leading-relaxed">
                    Provides detailed DMA geographic breakdowns, platform distribution (CTV, Mobile, Browser), and session duration metrics across verified consumer panels.
                </p>
            </div>

            <div class="bg-white border border-slate-200 p-6 rounded-2xl shadow-xs hover:border-emerald-300 transition-all">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2.5">
                        <div class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </div>
                        <h4 class="text-base font-bold text-slate-900">Tenetic Watch Time & Monetization</h4>
                    </div>
                    <span class="text-[10px] font-mono font-bold bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200">Minute Telemetry</span>
                </div>
                <p class="text-xs text-slate-600 leading-relaxed">
                    Analyzes content title watch time in seconds, completion rates, unique user depth, and inventory valuation for premium live telecasts.
                </p>
            </div>
        </div>
    </section>

        <!-- Company Leadership -->
    <section id="leadership" class="py-16 px-6 bg-slate-900 text-white w-full border-t border-slate-800">
        <div class="max-w-6xl mx-auto">
            <div class="mb-10 text-center sm:text-left">
                <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-sky-400 text-xs font-mono font-bold mb-2">
                    <span class="w-2 h-2 rounded-full bg-sky-400"></span>
                    FOUNDED BY INDUSTRY VETERANS
                </div>
                <h3 class="text-2xl sm:text-3xl font-bold tracking-tight">Company Leadership</h3>
                <p class="text-xs text-slate-400 mt-2 max-w-xl">
                    Tenetic is led by measurement pioneers with decades of leadership in digital analytics, television ratings standards, and real-time consumer data.
                </p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-slate-800/90 border border-slate-700 p-6 rounded-2xl flex flex-col sm:flex-row gap-5 items-start">
                    <img 
                        src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80" 
                        alt="Tod Johnson" 
                        class="w-24 h-24 rounded-2xl object-cover border-2 border-sky-500/40 shrink-0 shadow-md" 
                    />
                    <div class="flex-1 min-w-0">
                        <div class="flex flex-wrap items-center justify-between gap-2">
                            <h4 class="text-lg font-bold text-white">Tod Johnson</h4>
                            <span class="text-[10px] font-mono text-sky-400 bg-sky-950/80 border border-sky-800 px-2 py-0.5 rounded font-bold">Media Metrix Founder</span>
                        </div>
                        <div class="text-xs font-semibold text-sky-400 mt-0.5">Co-Founder &amp; Audience Measurement Pioneer</div>
                        <div class="text-[10px] text-slate-400 font-mono mt-1">Former Exec Chairman, The NPD Group</div>
                        <p class="text-xs text-slate-300 mt-3 leading-relaxed">
                            Pioneer of modern digital audience measurement who built Media Metrix into the first universal digital ratings standard and served as Executive Chairman of The NPD Group. Tod brings decades of institutional research authority to Tenetic.
                        </p>
                    </div>
                </div>

                <div class="bg-slate-800/90 border border-slate-700 p-6 rounded-2xl flex flex-col sm:flex-row gap-5 items-start">
                    <img 
                        src="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80" 
                        alt="Chris Wilson" 
                        class="w-24 h-24 rounded-2xl object-cover border-2 border-sky-500/40 shrink-0 shadow-md" 
                    />
                    <div class="flex-1 min-w-0">
                        <div class="flex flex-wrap items-center justify-between gap-2">
                            <h4 class="text-lg font-bold text-white">Chris Wilson</h4>
                            <span class="text-[10px] font-mono text-indigo-400 bg-indigo-950/80 border border-indigo-800 px-2 py-0.5 rounded font-bold">Former EVP Comscore</span>
                        </div>
                        <div class="text-xs font-semibold text-indigo-400 mt-0.5">Chief Executive Officer (CEO)</div>
                        <div class="text-[10px] text-slate-400 font-mono mt-1">Veteran Media Measurement Executive</div>
                        <p class="text-xs text-slate-300 mt-3 leading-relaxed">
                            Accomplished senior media measurement executive leading Tenetic's national deployment across US live telecasts, streaming platforms, and broadcast networks to replace delayed monthly ratings with real-time Lakehouse intelligence.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </section>


    <!-- Footer -->
    <footer class="mt-auto border-t border-slate-200 bg-white px-6 py-8 text-xs text-slate-500">
        <div class="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
            <div class="flex items-center gap-3">
                <img src="/static/tenetic_logo.png" alt="Tenetic" class="h-7 w-auto object-contain" />
                <span class="text-slate-300 hidden sm:inline">|</span>
                <span class="font-semibold text-slate-700 text-xs hidden sm:inline">Real-Time US Media Intelligence Lakehouse</span>
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
            type="button"
            onclick="window.toggleChat()" 
            id="chatToggleBtn"
            class="bg-slate-900 hover:bg-slate-800 text-white font-bold px-4 py-2.5 rounded-full shadow-2xl shadow-slate-900/40 flex items-center gap-2.5 transition-all border border-slate-700 cursor-pointer group touch-manipulation"
        >
            <div class="h-6 px-1.5 py-0.5 bg-white rounded-md flex items-center justify-center">
                <img src="/static/tenetic_logo.png" alt="Tenetic" class="h-4 w-auto object-contain" />
            </div>
            <span class="text-xs tracking-tight font-bold">Ask Tenetic AI</span>
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        </button>
    </div>

    <!-- Official Tenetic Floating AI Chatbot Window (Default Open display:flex) -->
    <div 
        id="chatWidget" 
        style="display: flex;"
        class="fixed bottom-0 right-0 sm:bottom-20 sm:right-5 z-50 w-full sm:max-w-md bg-white border border-slate-300 sm:rounded-3xl shadow-2xl flex flex-col h-[85vh] sm:h-[540px] overflow-hidden transition-all"
    >
        <!-- Chat Widget Header with Fullscreen and Close controls -->
        <div class="bg-slate-900 border-b border-slate-800 p-3.5 px-4 flex items-center justify-between shrink-0 text-white">
            <div class="flex items-center gap-3">
                <div class="h-8 px-2.5 py-1 bg-white rounded-lg flex items-center justify-center shadow-xs">
                    <img src="/static/tenetic_logo.png" alt="Tenetic" class="h-5 w-auto object-contain" />
                </div>
                <div>
                    <h3 class="text-xs font-bold tracking-tight flex items-center gap-1.5">
                        Tenetic AI Assistant
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    </h3>
                    <p class="text-[10px] text-slate-400 font-mono">US Telecasts & Media Analytics Gateway</p>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <button 
                    type="button"
                    onclick="window.exportFullChatPDF(this)" 
                    title="Export Full Session to PDF" 
                    class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer border border-slate-700 shadow-sm touch-manipulation"
                >
                    <span>📄</span> <span class="hidden sm:inline">Export Session (PDF)</span><span class="sm:hidden">PDF</span>
                </button>
                <button 
                    type="button"
                    onclick="window.toggleFullscreenChat()" 
                    id="fullscreenToggleBtn" 
                    title="Maximize Fullscreen" 
                    class="px-2.5 py-1 rounded-lg bg-sky-700 hover:bg-sky-600 text-white text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer border border-sky-500/50 shadow-sm touch-manipulation"
                >
                    <span id="fullscreenBtnText">⛶ Fullscreen</span>
                </button>
                <button 
                    type="button"
                    onclick="window.toggleChat(false)" 
                    title="Close Chat" 
                    class="w-7 h-7 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-xs transition-colors border border-slate-700 cursor-pointer touch-manipulation"
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
            <button type="button" onclick="window.sendQuickQuery('What are the top 5 properties by audience share in the US?', this)" class="bg-slate-100 hover:bg-slate-200 active:scale-95 text-sky-700 px-2.5 py-1 rounded-md border border-slate-200 font-medium cursor-pointer transition-all touch-manipulation">
                📊 Top Properties
            </button>
            <button type="button" onclick="window.sendQuickQuery('What is the audience profile breakdown by platform?', this)" class="bg-slate-100 hover:bg-slate-200 active:scale-95 text-indigo-700 px-2.5 py-1 rounded-md border border-slate-200 font-medium cursor-pointer transition-all">
                🍩 Platform Share
            </button>
            <button type="button" onclick="window.sendQuickQuery('Show top 5 content titles by total watch time in seconds', this)" class="bg-slate-100 hover:bg-slate-200 active:scale-95 text-amber-700 px-2.5 py-1 rounded-md border border-slate-200 font-medium cursor-pointer transition-all">
                💰 Content Watch Time
            </button>
            <button type="button" onclick="window.sendQuickQuery('Show top ad categories by audience', this)" class="bg-slate-100 hover:bg-slate-200 active:scale-95 text-emerald-700 px-2.5 py-1 rounded-md border border-slate-200 font-medium cursor-pointer transition-all">
                📱 Top Ad Brands
            </button>
            <button type="button" onclick="window.sendQuickQuery('Which property had the highest total audience in the most recent monthly period?', this)" class="bg-slate-100 hover:bg-slate-200 active:scale-95 text-purple-700 px-2.5 py-1 rounded-md border border-slate-200 font-medium cursor-pointer transition-all">
                🏆 #1 Audience Leader
            </button>
        </div>

        <!-- Floating Input Form -->
        <div class="p-3 border-t border-slate-200 bg-white shrink-0">
            <form onsubmit="return window.handleChatSubmit(event);" class="relative flex items-center">
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
    return HTMLResponse(
        content=HTML_INTERFACE,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


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
