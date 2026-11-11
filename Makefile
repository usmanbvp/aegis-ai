PYTHON ?= python
VENV ?= .venv
PIP := $(VENV)/Scripts/python -m pip
PYTHON_RUN := $(VENV)/Scripts/python

.PHONY: install lint test check smoke demo run-backend run-frontend docker-up docker-down

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]

lint:
	$(PYTHON_RUN) -m ruff check backend
	$(PYTHON_RUN) -m black --check backend

format:
	$(PYTHON_RUN) -m black backend
	$(PYTHON_RUN) -m ruff check --fix backend

test:
	$(PYTHON_RUN) -m pytest backend/tests -q

check: lint test

smoke:
	$(PYTHON_RUN) -m pytest backend/tests -q
	cd frontend && npm run build

demo:
	$(PYTHON_RUN) scripts/demo_incident_flow.py --incident INC-001

run-backend:
	cd backend && $(PYTHON_RUN) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	npm --prefix frontend install
	npm --prefix frontend run dev -- --host 0.0.0.0

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v
