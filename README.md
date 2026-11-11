# AEGIS — AI Incident Investigation & Root-Cause Agent

AEGIS is a working AI incident investigation system that correlates evidence from documentation, logs, metrics, and deployment metadata to produce an evidence-backed root-cause analysis and approval flow.

## Current status

This repository now contains a functional V1 implementation of the AEGIS system, including:

- FastAPI backend with incident investigation routes
- Retrieval pipeline for relevant incident evidence
- Synthetic engineering dataset generation and database persistence
- Incident approval history tracking with persisted decisions
- LangGraph orchestration for investigation workflow execution
- React + Vite frontend connected to the backend API
- Project-level test coverage for the backend and frontend build validation

## What the system does

AEGIS investigates a service incident by:

1. Loading a target incident identifier
2. Retrieving relevant docs, logs, service context, and runtime evidence
3. Correlating the material into a structured investigation timeline
4. Producing a root-cause summary and recommended remediation
5. Prompting for human approval before advancing the change
6. Persisting the resulting decision history for future review

## Project architecture

- Backend: Python, FastAPI, SQLAlchemy, LangGraph, hybrid retrieval
- Frontend: React, TypeScript, Vite
- Storage: SQLite-first local database for local development; project scaffolding supports broader deployment patterns
- Workflow: graph-based orchestration for retrieval, evidence collection, synthesis, and recommendations

## Local setup

```bash
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e .[dev]
```

## Run the app

One-command local startup:

```bash
.venv\Scripts\python scripts/run_dev.py
```

This starts the backend and frontend together on free local ports and prints the active URLs.

Backend:

```bash
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
npm --prefix frontend install
npm --prefix frontend run dev -- --host 0.0.0.0
```

### Quick demo flow

1. Start the backend on port 8000.
2. Start the frontend in development mode.
3. Open the app and choose an incident.
4. Click Investigate and then Approve or Reject.
5. Confirm the approval decision is saved in the incident history.

```bash
.venv\Scripts\python scripts/demo_incident_flow.py --base-url http://127.0.0.1:8000 --incident INC-001
```

## API endpoints

- GET /health
- GET /api/v1/health
- POST /api/v1/investigations/analyze
- POST /api/v1/investigations/approve
- GET /api/v1/investigations/history/{incident_id}

Example payload for investigation:

```json
{
  "incident_id": "INC-1001"
}
```

Example approval payload:

```json
{
  "incident_id": "INC-1001",
  "decision": "approve"
}
```

## Testing

```bash
.venv\Scripts\python -m pytest backend/tests -q
```

Frontend validation:

```bash
cd frontend
npm run build
```

## Environment configuration

Copy `.env.example` to `.env` and configure `GROQ_API_KEY`, `GEMINI_API_KEY`, or both. Groq is tried first by default and Gemini is used as fallback; if only one key is configured, only that provider is called. Provider requests use bounded retries, and investigation responses identify the provider actually used. If every configured provider fails, AEGIS returns an evidence-only fallback and records a non-secret failure code.

Check every configured provider against its live API:

```powershell
.venv\Scripts\python.exe scripts/check_llm_providers.py
```

This sends a minimal test prompt to each configured provider. It does not print API keys or provider response bodies.
Investigation prompts include incident descriptions, retrieved documents, deployment metadata, logs, and metrics. Only send data to providers approved for that data classification; do not include credentials or regulated data unless the provider policy permits it.

## Operational notes

The system is intentionally designed to stay simple and testable: local-first persistence, deterministic synthetic datasets, and explicit approval checkpoints make it suitable for iterative iteration and demonstration work without needing an external production stack.

## Next-phase use

This implementation is ready for incremental improvements such as richer retrieval tuning, tighter evaluation, improved UI states, and a broader deployment setup.
