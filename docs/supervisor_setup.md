# Databricks Genie Multi-Agent Supervisor Setup Guide

The **Supervisor Service** is a standalone web application and API gateway that routes natural language questions to one of 4 domain-specific Databricks Genie agents (`audience_reach`, `engagement`, `composition`, `monetization`) via Databricks Managed MCP Endpoints (`https://{host}/api/2.0/mcp/genie/{space_id}`).

---

## 1. Environment Configuration

Copy `supervisor/.env.example` or create a `.env` file with the following variables:

```ini
# Databricks Workspace Connection
DATABRICKS_HOST=dbc-aa73f553-354d.cloud.databricks.com
DATABRICKS_TOKEN=your_token_here

# Databricks Genie Space IDs per Domain
GENIE_SPACE_ID_AUDIENCE=01f1a1fd42bf12c9b418f72e196ce123
GENIE_SPACE_ID_ENGAGEMENT=01f1a6065b871342b326e101c2469fb2
GENIE_SPACE_ID_COMPOSITION=01f1a6061e7110a69b5c9b4d3ccc16b4
GENIE_SPACE_ID_MONETIZATION=01f1a605b30a1a06ae28b8f2fc484f56
```

---

## 2. Where to Find Genie Space IDs

To locate the Space ID for each domain's Databricks Genie agent:

1. Log into your Databricks workspace (`https://dbc-aa73f553-354d.cloud.databricks.com`).
2. In the left navigation sidebar, navigate to **Genie**.
3. Select the Genie Space corresponding to the target domain (e.g., *Audience Reach Genie Agent*).
4. Look at your browser address bar URL:
   `https://<workspace_host>/genie/spaces/<GENIE_SPACE_ID>/...`
5. Copy the 32-character ID string (e.g., `01f1a1fd42bf12c9b418f72e196ce123`) and paste it into the matching environment variable (`GENIE_SPACE_ID_AUDIENCE`, `GENIE_SPACE_ID_ENGAGEMENT`, etc.).

---

## 3. Running the Supervisor Service

### Option A: Docker Compose Deployment (Recommended for EC2)

Deploy the entire stack including supervisor on port `8001`:

```bash
docker compose -f docker/docker-compose.yml up -d --build supervisor
```

Check health status:
```bash
curl http://localhost:8001/health
```

### Option B: Local Development Execution

Run locally with `uv`:

```bash
uv run python -m uvicorn supervisor.app:app --host 0.0.0.0 --port 8001 --reload
```

---

## 4. Opening the Web Interface

Once deployed, access the web chat interface in any browser:

- **Local URL**: `http://localhost:8001`
- **EC2 / Production URL**: `http://<EC2_PUBLIC_IP>:8001`

### Web Interface Features:
1. **Interactive Chat Input**: Type any analytical question (e.g., *"Which property had the highest audience last month?"* or *"What is the average CPM by platform?"*).
2. **Domain Badges**: The interface displays a colored domain badge (`AUDIENCE REACH`, `ENGAGEMENT`, `COMPOSITION`, `MONETIZATION`) above each answer showing which Genie agent processed the query.
