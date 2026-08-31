"""
validation/genie_client_portal.py

Method C Implementation: Interactive Client Web Portal powered by Databricks Genie REST API.

Allows external clients/stakeholders to ask natural language questions directly 
from a custom web interface without needing Databricks workspace access.

Usage:
  uv run python validation/genie_client_portal.py --port 8050

Requires:
  DATABRICKS_HOST
  DATABRICKS_TOKEN
  GENIE_SPACE_ID
"""

import argparse
import logging
import os
import sys

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from validation.genie_validator import GenieClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("genie_portal")

app = FastAPI(title="Media Analytics Client Portal")


class QuestionRequest(BaseModel):
    question: str


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Media Analytics AI Portal | Powered by Databricks Genie</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .hero-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 16px; padding: 2rem; margin-top: 2rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        .btn-brand { background-color: #ff3621; color: white; font-weight: 600; border-radius: 8px; padding: 0.6rem 1.5rem; border: none; }
        .btn-brand:hover { background-color: #e02d18; color: white; }
        .sql-box { background-color: #020617; border: 1px solid #1e293b; border-radius: 8px; padding: 1rem; color: #38bdf8; font-family: monospace; white-space: pre-wrap; }
        .answer-box { background-color: #1e293b; border-left: 4px solid #38bdf8; padding: 1rem; margin-bottom: 1rem; border-radius: 4px; }
        .badge-genie { background-color: #0284c7; color: white; padding: 0.4em 0.8em; border-radius: 20px; font-size: 0.85rem; }
    </style>
</head>
<body>
<div class="container pb-5">
    <div class="hero-card text-center">
        <span class="badge-genie mb-2">Powered by Databricks Genie AI</span>
        <h1 class="fw-bold mt-2">Media Analytics Natural Language Assistant</h1>
        <p class="text-secondary">Ask any analytical question about audience metrics, property rankings, or distribution platforms.</p>

        <div class="row justify-content-center mt-4">
            <div class="col-md-9">
                <div class="input-group input-group-lg">
                    <input type="text" id="userQuestion" class="form-control bg-dark text-white border-secondary" placeholder="e.g. Which property had the highest audience last quarter?" value="Which property had the highest audience last quarter?">
                    <button class="btn btn-brand" type="button" id="askBtn" onclick="askGenie()">Ask AI</button>
                </div>
            </div>
        </div>
    </div>

    <div id="loading" class="text-center my-4 d-none">
        <div class="spinner-border text-info" role="status"></div>
        <p class="mt-2 text-secondary">Genie AI is analyzing your data & generating SQL...</p>
    </div>

    <div id="results" class="hero-card d-none">
        <h4 class="fw-bold text-info mb-3">AI Response</h4>
        <div id="answerText" class="answer-box fs-5"></div>

        <h5 class="fw-bold text-secondary mt-4">Generated Databricks SQL</h5>
        <div id="generatedSql" class="sql-box"></div>
    </div>
</div>

<script>
async function askGenie() {
    const q = document.getElementById('userQuestion').value.trim();
    if (!q) return;

    document.getElementById('loading').classList.remove('d-none');
    document.getElementById('results').classList.add('d-none');
    document.getElementById('askBtn').disabled = true;

    try {
        const resp = await fetch('/api/ask', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({question: q})
        });
        const data = await resp.json();

        document.getElementById('answerText').innerText = data.answer_text || 'No text answer returned.';
        document.getElementById('generatedSql').innerText = data.generated_sql || 'No SQL generated.';
        document.getElementById('results').classList.remove('d-none');
    } catch (e) {
        alert('Error asking Genie: ' + e);
    } finally {
        document.getElementById('loading').classList.add('d-none');
        document.getElementById('askBtn').disabled = false;
    }
}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_TEMPLATE


@app.post("/api/ask")
def ask_question(payload: QuestionRequest):
    host = os.environ.get("DATABRICKS_HOST", "https://dbc-aa73f553-354d.cloud.databricks.com")
    token = os.environ.get("DATABRICKS_TOKEN", "")
    space_id = os.environ.get("GENIE_SPACE_ID", "01f1a1fd42bf12c9b418f72e196ce123")

    if not token:
        raise HTTPException(status_code=500, detail="DATABRICKS_TOKEN env var not set.")

    client = GenieClient(host=host, token=token, space_id=space_id)
    res = client.ask(payload.question)
    return res


def main():
    parser = argparse.ArgumentParser(description="Genie Client Portal Web App")
    parser.add_argument("--port", type=int, default=8050, help="Port to run portal on")
    args = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
