# =============================================================================
# NL2SQL Thesis Application — Makefile
# =============================================================================
# Single entry point for running, building, and managing the app.
# Run `make help` (or just `make`) to see all available targets.
# =============================================================================

SHELL := /usr/bin/env bash

# Paths
ROOT        := $(shell pwd)
BACKEND     := $(ROOT)/backend
FRONTEND    := $(ROOT)/frontend
VENV        := $(BACKEND)/venv
VENV_BIN    := $(VENV)/bin
PY          := $(VENV_BIN)/python
PIP         := $(VENV_BIN)/pip

# Ports
BACKEND_PORT  := 8000
FRONTEND_PORT := 3050

# Env file preference: .env.local wins over .env when present
ENV_FILE := $(shell if [ -f "$(ROOT)/.env.local" ]; then echo "$(ROOT)/.env.local"; else echo "$(ROOT)/.env"; fi)

# Docker compose file selection
COMPOSE         := docker compose
COMPOSE_LOCAL   := docker-compose.yml
COMPOSE_EXPOSE  := docker-compose.expose.yml

# Colors
C_RESET := \033[0m
C_BOLD  := \033[1m
C_BLUE  := \033[0;34m
C_GREEN := \033[0;32m
C_YELL  := \033[1;33m
C_RED   := \033[0;31m

.DEFAULT_GOAL := help
.PHONY: help install install-backend install-frontend migrate embed \
        dev dev-backend dev-frontend build start \
        stop status clean clean-backend clean-frontend \
        test test-backend lint format \
        docker docker-up docker-down docker-logs docker-expose docker-urls docker-rebuild \
        check-env check-venv check-node

# =============================================================================
# Help
# =============================================================================

help:  ## Show this help
	@printf "$(C_BOLD)NL2SQL Thesis Application$(C_RESET)\n\n"
	@printf "$(C_BOLD)Setup$(C_RESET)\n"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / && /^(install|migrate|embed)/ {printf "  $(C_GREEN)%-18s$(C_RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf "\n$(C_BOLD)Local development$(C_RESET)\n"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / && /^(dev|build|start|stop|status|test|lint|format)/ {printf "  $(C_GREEN)%-18s$(C_RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf "\n$(C_BOLD)Docker$(C_RESET)\n"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / && /^docker/ {printf "  $(C_GREEN)%-18s$(C_RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf "\n$(C_BOLD)Maintenance$(C_RESET)\n"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / && /^clean/ {printf "  $(C_GREEN)%-18s$(C_RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf "\nUsing env file: $(C_YELL)$(ENV_FILE)$(C_RESET)\n"

# =============================================================================
# Setup
# =============================================================================

install: install-backend install-frontend  ## Install backend venv + frontend node_modules

install-backend: check-env  ## Create Python venv and install backend requirements
	@printf "$(C_BLUE)→ Setting up backend venv$(C_RESET)\n"
	@if [ ! -d "$(VENV)" ]; then python3 -m venv "$(VENV)"; fi
	@$(PIP) install --upgrade pip
	@$(PIP) install -r $(BACKEND)/requirements.txt
	@printf "$(C_GREEN)✓ Backend deps installed$(C_RESET)\n"

install-frontend:  ## Install frontend node_modules
	@printf "$(C_BLUE)→ Installing frontend deps$(C_RESET)\n"
	@cd $(FRONTEND) && npm install
	@printf "$(C_GREEN)✓ Frontend deps installed$(C_RESET)\n"

migrate: check-venv  ## Apply pending database migrations
	@printf "$(C_BLUE)→ Running migrations$(C_RESET)\n"
	@cd $(BACKEND) && set -a && . $(ENV_FILE) && set +a && $(PY) run_migration.py

embed: check-venv  ## Build AdventureWorks schema embeddings for RAG (first-time only)
	@printf "$(C_BLUE)→ Generating schema embeddings$(C_RESET)\n"
	@cd $(BACKEND) && set -a && . $(ENV_FILE) && set +a && $(PY) -m rag_engine.embeddings

# =============================================================================
# Local development (foreground; run in two terminals)
# =============================================================================

dev: check-env check-venv check-node  ## Run backend + frontend locally in parallel (Ctrl+C stops both)
	@printf "$(C_BLUE)→ Starting backend :$(BACKEND_PORT) and frontend :$(FRONTEND_PORT)$(C_RESET)\n"
	@printf "$(C_YELL)  Press Ctrl+C to stop both.$(C_RESET)\n\n"
	@trap 'kill 0 2>/dev/null' INT TERM EXIT; \
	( cd $(BACKEND) && set -a && . $(ENV_FILE) && set +a && $(PY) main.py 2>&1 | sed -u 's/^/[backend ] /' ) & \
	( cd $(FRONTEND) && npm run dev 2>&1 | sed -u 's/^/[frontend] /' ) & \
	wait

dev-backend: check-venv  ## Run backend with hot reload on :8000
	@printf "$(C_BLUE)→ Starting backend on http://localhost:$(BACKEND_PORT)$(C_RESET)\n"
	@cd $(BACKEND) && set -a && . $(ENV_FILE) && set +a && $(PY) main.py

dev-frontend: check-node  ## Run frontend dev server on :3050
	@printf "$(C_BLUE)→ Starting frontend on http://localhost:$(FRONTEND_PORT)$(C_RESET)\n"
	@cd $(FRONTEND) && npm run dev

build: check-node  ## Production build of the frontend
	@cd $(FRONTEND) && npm run build

start: check-node  ## Production start of the frontend (after `make build`)
	@cd $(FRONTEND) && npm run start -- -p $(FRONTEND_PORT)

# =============================================================================
# Lifecycle
# =============================================================================

stop:  ## Kill local processes on backend and frontend ports
	@printf "$(C_BLUE)→ Stopping local servers$(C_RESET)\n"
	@pids=$$(lsof -ti:$(BACKEND_PORT) 2>/dev/null);  [ -z "$$pids" ] || echo "$$pids" | xargs kill -9 2>/dev/null && printf "  $(C_GREEN)✓ backend stopped$(C_RESET)\n" || printf "  backend not running\n"
	@pids=$$(lsof -ti:$(FRONTEND_PORT) 2>/dev/null); [ -z "$$pids" ] || echo "$$pids" | xargs kill -9 2>/dev/null && printf "  $(C_GREEN)✓ frontend stopped$(C_RESET)\n" || printf "  frontend not running\n"

status:  ## Show PostgreSQL, Redis, backend, and frontend status
	@printf "$(C_BOLD)System status$(C_RESET)\n"
	@pg_isready -h localhost -p 5432 >/dev/null 2>&1 && printf "  $(C_GREEN)✓$(C_RESET) PostgreSQL\n" || printf "  $(C_RED)✗$(C_RESET) PostgreSQL\n"
	@redis-cli ping >/dev/null 2>&1            && printf "  $(C_GREEN)✓$(C_RESET) Redis\n"      || printf "  $(C_YELL)!$(C_RESET) Redis (optional)\n"
	@lsof -ti:$(BACKEND_PORT) >/dev/null 2>&1  && printf "  $(C_GREEN)✓$(C_RESET) Backend  (:$(BACKEND_PORT))\n"  || printf "  $(C_RED)✗$(C_RESET) Backend  (:$(BACKEND_PORT))\n"
	@lsof -ti:$(FRONTEND_PORT) >/dev/null 2>&1 && printf "  $(C_GREEN)✓$(C_RESET) Frontend (:$(FRONTEND_PORT))\n" || printf "  $(C_RED)✗$(C_RESET) Frontend (:$(FRONTEND_PORT))\n"
	@curl -sf http://localhost:$(BACKEND_PORT)/health >/dev/null && printf "  $(C_GREEN)✓$(C_RESET) Backend /health\n" || printf "  $(C_YELL)!$(C_RESET) Backend /health not responding\n"

# =============================================================================
# Quality
# =============================================================================

test: test-backend  ## Run test suites

test-backend: check-venv  ## Run backend pytest
	@cd $(BACKEND) && set -a && . $(ENV_FILE) && set +a && $(VENV_BIN)/pytest -v

test-shared-account: check-venv  ## Regression test for the Prolific shared-account fix (needs RAILWAY_DB_URL env)
	@cd $(BACKEND) && $(PY) -m tests.test_shared_account_fix

test-readiness: check-venv  ## Pre-launch readiness check for the next study run (needs RAILWAY_DB_URL env)
	@cd $(BACKEND) && $(PY) -m tests.test_study_readiness

test-resolution: check-venv  ## Regression: concurrent participant resolution under shared accounts (needs RAILWAY_DB_URL env)
	@cd $(BACKEND) && $(PY) -m tests.test_concurrent_resolution

lint:  ## Lint backend (ruff) and frontend (next lint)
	@cd $(BACKEND) && $(VENV_BIN)/ruff check . || true
	@cd $(FRONTEND) && npm run lint || true

format:  ## Format backend (black + ruff --fix)
	@cd $(BACKEND) && $(VENV_BIN)/black . && $(VENV_BIN)/ruff check --fix .

# =============================================================================
# Docker
# =============================================================================

docker: docker-up  ## Alias for docker-up

docker-up: check-env  ## Build and start the full stack with Docker Compose
	@printf "$(C_BLUE)→ Starting stack via Docker$(C_RESET)\n"
	@$(COMPOSE) -f $(COMPOSE_LOCAL) up -d --build
	@printf "$(C_GREEN)✓ Stack running$(C_RESET)  frontend: http://localhost:$(FRONTEND_PORT)  backend: http://localhost:$(BACKEND_PORT)\n"

docker-down:  ## Stop all Docker containers (local + exposed)
	@$(COMPOSE) -f $(COMPOSE_LOCAL) down 2>/dev/null || true
	@$(COMPOSE) -f $(COMPOSE_EXPOSE) down 2>/dev/null || true
	@printf "$(C_GREEN)✓ Containers stopped$(C_RESET)\n"

docker-logs:  ## Tail Docker logs (auto-detects local vs exposed stack)
	@if docker ps | grep -q "thesis-tunnel"; then \
		$(COMPOSE) -f $(COMPOSE_EXPOSE) logs -f; \
	else \
		$(COMPOSE) -f $(COMPOSE_LOCAL) logs -f; \
	fi

docker-rebuild: check-env  ## Force rebuild of Docker images
	@$(COMPOSE) -f $(COMPOSE_LOCAL) build --no-cache

docker-expose: check-env  ## Start stack with Cloudflare tunnels (public URLs for participants)
	@printf "$(C_BLUE)→ Starting backend and backend tunnel$(C_RESET)\n"
	@$(COMPOSE) -f $(COMPOSE_EXPOSE) up -d --build backend tunnel-backend
	@sleep 8
	@BACKEND_URL=$$(docker logs thesis-tunnel-backend 2>&1 | grep -o 'https://[^[:space:]]*trycloudflare.com' | tail -1); \
	if [ -z "$$BACKEND_URL" ]; then sleep 5; BACKEND_URL=$$(docker logs thesis-tunnel-backend 2>&1 | grep -o 'https://[^[:space:]]*trycloudflare.com' | tail -1); fi; \
	if [ -z "$$BACKEND_URL" ]; then printf "$(C_RED)✗ Could not get backend tunnel URL. Check: docker logs thesis-tunnel-backend$(C_RESET)\n"; exit 1; fi; \
	printf "$(C_GREEN)✓ Backend tunnel: %s$(C_RESET)\n" "$$BACKEND_URL"; \
	printf "$(C_BLUE)→ Building frontend with that backend URL baked in$(C_RESET)\n"; \
	$(COMPOSE) -f $(COMPOSE_EXPOSE) build --build-arg NEXT_PUBLIC_API_URL="$$BACKEND_URL" frontend; \
	$(COMPOSE) -f $(COMPOSE_EXPOSE) up -d frontend tunnel-frontend; \
	sleep 8; \
	FRONTEND_URL=$$(docker logs thesis-tunnel-frontend 2>&1 | grep -o 'https://[^[:space:]]*trycloudflare.com' | tail -1); \
	if [ -z "$$FRONTEND_URL" ]; then sleep 5; FRONTEND_URL=$$(docker logs thesis-tunnel-frontend 2>&1 | grep -o 'https://[^[:space:]]*trycloudflare.com' | tail -1); fi; \
	printf "\n$(C_BOLD)Public URLs$(C_RESET)\n"; \
	printf "  Backend:  %s\n" "$$BACKEND_URL"; \
	printf "  $(C_GREEN)Frontend (share with participants): %s$(C_RESET)\n" "$$FRONTEND_URL"; \
	printf "\n$(C_YELL)! These Cloudflare quick-tunnel URLs are ephemeral; they change on restart.$(C_RESET)\n"

docker-urls:  ## Show active Cloudflare tunnel URLs
	@if ! docker ps | grep -q "thesis-tunnel"; then printf "$(C_RED)✗ Tunnels not running. Start with: make docker-expose$(C_RESET)\n"; exit 1; fi
	@BACKEND_URL=$$(docker logs thesis-tunnel-backend 2>&1 | grep -o 'https://[^[:space:]]*trycloudflare.com' | tail -1); \
	FRONTEND_URL=$$(docker logs thesis-tunnel-frontend 2>&1 | grep -o 'https://[^[:space:]]*trycloudflare.com' | tail -1); \
	printf "  Backend:  %s\n" "$${BACKEND_URL:-(not ready)}"; \
	printf "  Frontend: %s\n" "$${FRONTEND_URL:-(not ready)}"

# =============================================================================
# Clean
# =============================================================================

clean: clean-backend clean-frontend  ## Remove venv, node_modules, and build artifacts

clean-backend:  ## Remove backend venv and Python caches
	@rm -rf $(VENV) $(BACKEND)/__pycache__ $(BACKEND)/**/__pycache__ .pytest_cache .coverage htmlcov
	@printf "$(C_GREEN)✓ Backend cleaned$(C_RESET)\n"

clean-frontend:  ## Remove frontend node_modules and .next build
	@rm -rf $(FRONTEND)/node_modules $(FRONTEND)/.next $(FRONTEND)/tsconfig.tsbuildinfo
	@printf "$(C_GREEN)✓ Frontend cleaned$(C_RESET)\n"

# =============================================================================
# Guards
# =============================================================================

check-env:
	@if [ ! -f "$(ENV_FILE)" ]; then \
		printf "$(C_RED)✗ No env file found.$(C_RESET) Copy .env.example to .env and fill in credentials.\n"; \
		exit 1; \
	fi

check-venv:
	@if [ ! -x "$(PY)" ]; then \
		printf "$(C_RED)✗ Backend venv missing.$(C_RESET) Run: $(C_GREEN)make install-backend$(C_RESET)\n"; \
		exit 1; \
	fi

check-node:
	@if [ ! -d "$(FRONTEND)/node_modules" ]; then \
		printf "$(C_RED)✗ Frontend deps missing.$(C_RESET) Run: $(C_GREEN)make install-frontend$(C_RESET)\n"; \
		exit 1; \
	fi
