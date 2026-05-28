.PHONY: install install-backend install-frontend dev-backend dev-frontend dev test lint clean help

PYTHON  := python3
VENV    := .venv
PIP     := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn

# ── Setup ─────────────────────────────────────────────────────────────────────

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Set up Python virtualenv and install backend deps
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "\n✓ Backend ready. Activate with: source $(VENV)/bin/activate"

install-frontend: ## Install frontend npm dependencies
	cd frontend && npm install
	@echo "\n✓ Frontend ready."

# ── Dev servers ───────────────────────────────────────────────────────────────

dev-backend: ## Start the backend API server (hot-reload)
	$(UVICORN) backend.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend: ## Start the Next.js dev server
	cd frontend && npm run dev

dev: ## Start backend and frontend in parallel (requires two terminals — see README)
	@echo "Run each in its own terminal:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"

# ── Quality ───────────────────────────────────────────────────────────────────

test: ## Run backend test suite
	$(VENV)/bin/pytest tests/ -v

lint: ## Lint backend with mypy
	$(VENV)/bin/mypy backend/

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean: ## Remove virtualenv and generated files
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache
	find . -name "*.pyc" -delete

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up: ## Start full stack with docker-compose
	docker compose up --build

docker-down: ## Stop docker-compose stack
	docker compose down

# ── Help ──────────────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
