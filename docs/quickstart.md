# AEGIS quickstart

This guide covers the current local workflow for running the incident investigation system.

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm

## 1) Create the environment

```bash
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e .[dev]
```

## 2) Configure environment values

```bash
copy .env.example .env
```

Update the local values as needed for your environment.

## 3) Start the backend

From the repo root:

```bash
.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## 4) Start the frontend

```bash
npm --prefix frontend install
npm --prefix frontend run dev -- --host 0.0.0.0
```

Then open the frontend URL shown in the Vite output, usually http://localhost:5173.

## 5) Exercise the incident flow

Send an investigation request:

```bash
curl -X POST http://localhost:8000/api/v1/investigations/analyze \
  -H "Content-Type: application/json" \
  -d '{"incident_id":"INC-1001"}'
```

Approve the recommendation:

```bash
curl -X POST http://localhost:8000/api/v1/investigations/approve \
  -H "Content-Type: application/json" \
  -d '{"incident_id":"INC-1001","decision":"approve"}'
```

View approval history:

```bash
curl http://localhost:8000/api/v1/investigations/history/INC-1001
```

## 6) Run validation

```bash
.venv\Scripts\python -m pytest backend/tests -q
cd frontend
npm run build
```

## Notes

- The project uses a SQLite-first local database for rapid local iteration.
- The system is intentionally simple and human-in-the-loop so it remains demonstrable and testable.
