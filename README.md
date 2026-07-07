# NL2SQL Conversational BI: Thesis Experiment

Master's thesis project (TU Graz) studying conversational Business Intelligence with a Natural Language to SQL (NL2SQL) assistant. The application runs a between-subjects A/B experiment comparing traditional BI dashboards (control) against dashboards augmented with a multi-agent chatbot (experimental).

- **Database**: AdventureWorks sample DB (sales, production, HR)
- **Experiment**: participants complete 5 analytics tasks
- **Recruitment**: Prolific (completion code redirect built in)
- **Author**: Bolis Hakim

## Academic context

This repository is the software artefact of a Master's thesis in the joint **Computational Social Systems (CSS)** programme of the **University of Graz** and **Graz University of Technology (TU Graz)**, submitted for the degree of Master of Science.

- **Title**: Conversational Business Intelligence: An AI-Augmented Analytics Dashboard for Data-Driven Decision Making
- **Author**: Bolis Hakim
- **Degree**: MSc, Computational Social Systems (University of Graz / TU Graz)

**Supervised by:**

- Assoc.-Prof. Dr. Viktoria Pammer-Schindler — Institute of Human-Centred Computing, Graz University of Technology (TU Graz)
- Univ.-Prof. Dr. Stefan Thalmann — Institute of Operations and Information Systems, University of Graz

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, SQLAlchemy 2.0, LangGraph, Claude (Anthropic), OpenAI embeddings, PostgreSQL + pgvector, Redis |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind, Plotly.js, Recharts, SWR |
| Infra | Docker, Docker Compose, JWT auth |

## Multi-Agent Workflow

```
User query
    │
    ▼
Orchestrator (route: DIRECT_ANSWER | FULL_PIPELINE | INTERPRET_PREVIOUS | MODIFY_VISUALIZATION)
    │
    ▼
Schema Agent (RAG over pgvector)
    │
    ▼
SQL Agent ⇄ Validator  (retry loop, max 3)
    │
    ▼
Executor
    │
    ▼
Viz Generator
    │
    ▼
Accumulate Results
    │
    ▼
Iteration Decision (Analyst)  ⇄  Prepare Next Iteration  (query-iteration loop, max 3)
    │
    ▼
END (persist QueryHistory with full trace + token/cost metrics)
```

11 nodes, 15 edges, 3 conditional routes, 2 loops. See `backend/docs/workflow/` for the full diagram and node-level detail.

## Project Layout

```
thesis_nl2sql_app/
├── backend/              FastAPI + LangGraph (agents, services, RAG, API)
├── frontend/             Next.js App Router (onboarding, dashboards, chat, tasks, admin)
├── Makefile              All app commands (see `make help`)
├── docker-compose.yml    Local Docker stack
├── docker-compose.expose.yml   Docker + Cloudflare tunnels (public URLs)
└── .env.example          Env template
```

## Quick Start

Everything flows through `make`. Run `make help` to list all targets.

```bash
# 1. PostgreSQL with pgvector must be running and seeded with AdventureWorks
psql -U <user> -d Adventureworks -f backend/database/setup_database.sql

# 2. Configure environment
cp .env.example .env       # fill in DB creds, OPENAI_API_KEY, ANTHROPIC_API_KEY, JWT_SECRET_KEY

# 3. Install deps (backend venv + frontend node_modules)
make install

# 4. Apply DB migrations (001 to 007) and build schema embeddings
make migrate
make embed                 # first-time only

# 5. Run (two terminals)
make dev-backend           # terminal 1, http://localhost:8000
make dev-frontend          # terminal 2, http://localhost:3050
```

**Ports**: backend `8000`, frontend `3050`, API docs at `http://localhost:8000/docs`.

**Default accounts** (for local testing):
- Admin: `admin@thesis.local` / `admin123`
- Control: `user2@adventureworks.com` / `control123`
- Experimental: `user1@adventureworks.com` / `experiment123`

### Common make commands

| Command | Purpose |
|---------|---------|
| `make help` | List all targets |
| `make install` | Install backend + frontend deps |
| `make migrate` | Apply pending DB migrations |
| `make embed` | Build RAG schema embeddings (first-time) |
| `make dev-backend` | Run backend on :8000 |
| `make dev-frontend` | Run frontend dev server on :3050 |
| `make stop` | Kill local processes on the ports |
| `make status` | Show PostgreSQL / Redis / backend / frontend status |
| `make test` | Run backend pytest |
| `make lint` / `make format` | Lint / format |
| `make docker` | Build and start the full stack via Docker Compose |
| `make docker-down` | Stop Docker containers |
| `make docker-logs` | Tail Docker logs |
| `make docker-expose` | Start stack with Cloudflare tunnels (public URLs for participants) |
| `make docker-urls` | Show the active tunnel URLs |
| `make clean` | Remove venv, node_modules, build artifacts |

### Docker quick start

```bash
make docker          # build and start both services locally
make docker-logs     # tail logs
make docker-down     # stop
```

## Experiment Framework

Between-subjects design built into the data layer:

- **Participants**: anonymous, auto-generated codes (P001, P002, ...), balanced-random condition assignment (control vs experimental).
- **Tracked per task**: duration, answer + difficulty + confidence ratings, interaction count, chatbot queries (experimental only), dashboard actions.
- **Tracked per chatbot query**: full agent trace (orchestrator decision, retrieved tables, SQL + reasoning, validation issues, execution results, chart config, analyst insights), token usage, cost (USD), latency per stage.
- **Surveys**: pre-survey (7 anonymous demographic/experience questions), post-study TAM-based survey (dashboard and chatbot scales).

No PII is collected.

## Key Environment Variables

```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=Adventureworks
DATABASE_USER=postgres
DATABASE_PASSWORD=...

OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

REDIS_HOST=localhost
REDIS_PORT=6379

LLM_MODEL=claude-3-5-sonnet-20241022
EMBEDDING_MODEL=text-embedding-3-small
TOP_K_TABLES=5
ENABLE_ANCHOR_TABLES=true

API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
```

## Documentation Map

- [backend/README.md](backend/README.md): backend API, data model, agent workflow, setup
- [frontend/README.md](frontend/README.md): frontend pages, contexts, flows, setup
- [backend/docs/workflow/](backend/docs/workflow/): LangGraph workflow diagrams and node reference

## Repository

https://github.com/bolishakim/conversational-bi-nl2sql
