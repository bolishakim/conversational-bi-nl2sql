# Backend: NL2SQL AI Agent

FastAPI service backing the thesis experiment. Implements the multi-agent NL2SQL pipeline (LangGraph), the RAG layer (pgvector), the experiment data model, and all participant / admin APIs.

## Stack

- **Framework**: FastAPI 0.104 + Uvicorn
- **ORM**: SQLAlchemy 2.0
- **DB**: PostgreSQL 14+ with pgvector extension (AdventureWorks sample data)
- **LLM**: Anthropic Claude (Haiku for orchestrator routing, Sonnet for SQL / validation / visualization / analyst)
- **Embeddings**: OpenAI `text-embedding-3-small` (1536 dims)
- **Orchestration**: LangGraph
- **Cache**: Redis (optional)
- **Auth**: JWT (HS256) via python-jose, bcrypt password hashing

## Project Structure

```
backend/
├── main.py                      FastAPI entry; mounts 6 routers; lifespan env validation
├── run_migration.py             Applies SQL migrations in order, tracks applied ones
├── requirements.txt
│
├── api/                         REST API (52 endpoints total)
│   ├── auth.py                  /login, /me, /refresh, /logout
│   ├── chat.py                  /query, /query/stream (SSE)
│   ├── history.py               /stats, /{id}, DELETE /{id}
│   ├── dashboards.py            13 sales/production/operations endpoints
│   ├── experiment.py            onboarding, participants, tasks, interactions
│   ├── admin.py                 participant list, analytics, export
│   └── export.py                (placeholder)
│
├── agents/                      One package per agent (state + prompt + agent class)
│   ├── orchestrator/            Routes query (Haiku)
│   ├── schema/                  RAG retrieval (no LLM, uses embeddings)
│   ├── sql_agent/               Generates SQL (Sonnet)
│   ├── validator_agent/         Validates SQL (Sonnet)
│   ├── executor_agent/          Runs SQL, 30s timeout, 1000 row cap
│   ├── analyst_agent/           Iterative analysis + follow-up decision (Sonnet)
│   └── viz_generator_agent/     Chart type + config (Sonnet)
│
├── workflow/                    LangGraph definition (canonical)
│   ├── graph.py                 Nodes, edges, conditional routing
│   └── state.py                 WorkflowState TypedDict (50+ fields)
│
├── rag_engine/                  RAG over schema embeddings
│   ├── retriever.py             pgvector cosine + anchor-table strategy
│   ├── embeddings.py            Generate and store embeddings
│   ├── domain_detector.py       Classifies query domain
│   └── metadata.py              Anchor tables per domain
│
├── services/                    Business logic between API and workflow
│   ├── chat_service.py          Invokes workflow; formats response; SSE streaming
│   ├── history_service.py       Persists QueryHistory with full agent trace
│   └── experiment_service.py    Participant enrollment, task lifecycle, surveys
│
├── database/
│   ├── connection.py            SQLAlchemy engine + session
│   ├── models.py                All ORM models (see below)
│   ├── init_db.py               Schema init helper
│   ├── setup_database.sql       Bootstrap (pgvector, schemas, extensions)
│   └── migrations/              001 to 007 SQL files
│
├── config/
│   ├── settings.py              pydantic-settings (env-driven)
│   └── core_tables.py           Table metadata used by RAG embedding build
│
├── utils/
│   ├── security.py              JWT encode/decode, password hashing
│   ├── token_tracker.py         Aggregates per-call LLM token usage + cost
│   ├── conversation_compressor.py
│   ├── cache.py                 Redis helpers
│   ├── logger.py
│   └── database.py
│
├── templates/
│   └── join_paths.py            Common JOIN hints used by SQL Agent
│
└── docs/workflow/               Workflow diagrams (see README there)
```

Note: `orchestration/` exists but all files are empty. It's a leftover from an earlier refactor and is not used; safe to delete.

## Multi-Agent Workflow

11 nodes, 15 edges, 3 conditional routes, 2 loops. Full node/edge reference: `docs/workflow/WORKFLOW_STRUCTURE.md`.

### Nodes

1. **Orchestrator** (Haiku): decides `DIRECT_ANSWER`, `INTERPRET_PREVIOUS`, `MODIFY_VISUALIZATION`, or `FULL_PIPELINE`.
2. **Schema Agent**: pgvector RAG retrieval with anchor tables; no LLM call.
3. **SQL Agent** (Sonnet): generates SQL with chain-of-thought reasoning; receives validator feedback on retry.
4. **Validator** (Sonnet): schema and safety checks; emits structured issues.
5. **Executor**: runs validated SQL, returns rows + timing.
6. **Viz Generator** (Sonnet): selects chart type and config; non-critical (falls back to table).
7. **Accumulate Results**: appends current iteration to `all_query_results`.
8. **Iteration Decision** (Sonnet Analyst): decides if a follow-up query is needed.
9. **Prepare Next Iteration**: increments iteration counter, resets SQL retry count.
10. **Analyst**: same node class as Iteration Decision; runs iterative analysis over accumulated results.
11. **End**: finalizes state, computes total duration.

### Loops

- **SQL retry loop**: `validator → sql_agent` (max 3 retries; validator issues fed back to SQL Agent).
- **Query iteration loop**: `prepare_next_iteration → sql_agent → validator → executor → viz_generator → accumulate_results → iteration_decision` (max 3 iterations).

### Routing

- After Orchestrator: `DIRECT_ANSWER` → end; all other actions → Schema Agent.
- After Validator: valid → Executor; invalid + retry available → SQL Agent; invalid + max retries → End.
- After Iteration Decision: needs follow-up + under iteration cap → Prepare Next Iteration; otherwise → End.

## Database Schema

### Application tables (`public` schema)

| Table | Purpose |
|-------|---------|
| `users` | Auth only; role `admin` \| `participant_control` \| `participant_experimental` |
| `query_history` | Full per-query agent trace (orchestrator action, schema, SQL, reasoning, validation, execution, viz, analysis, tokens, cost, timings). FK to `experiment_participants` and `experiment_tasks` |
| `sessions` | JWT session tracking |
| `experiments` | A study instance |
| `experiment_participants` | Anonymous participant (code, condition, consent, pre-survey, post-survey, session stats) |
| `experiment_tasks` | Task-per-participant with timing + quality + efficiency outcomes |
| `experiment_interactions` | Per-action log (chatbot query or dashboard action) with tokens/cost |

### RAG tables (`rag` schema)

| Table | Purpose |
|-------|---------|
| `rag.table_embeddings` | AdventureWorks table metadata + 1536-dim embeddings with IVFFlat index |

### Migrations (in `database/migrations/`)

1. `001_extend_query_history.sql`
2. `002_create_experiment_schema.sql`
3. `003_add_participant_onboarding_fields.sql`
4. `004_add_participant_id_to_query_history.sql`
5. `005_add_presurvey_fields.sql`
6. `006_add_tutorial_fields.sql`
7. `007_update_presurvey_age_occupation.sql`

Run with `make migrate` from the repo root; applied migrations are tracked in `schema_migrations`.

## API Surface

### Auth (`/api/auth`)
`POST /login`, `GET /me`, `POST /refresh`, `POST /logout`

### Chat (`/api/chat`, experimental group only)
`POST /query`, `POST /query/stream` (SSE progress events)

### History (`/api/history`)
`GET /stats`, `GET /{query_id}`, `DELETE /{query_id}`

### Experiment (`/api/experiment`)
- Experiment CRUD: `POST /experiments`, `GET /experiments`, `GET /experiments/{id}`, `PATCH /experiments/{id}/status`, `GET /experiments/{id}/stats`
- Onboarding: `POST /onboarding/register`, `POST /onboarding/lookup`, `GET /onboarding/status`, `GET /onboarding/active-experiment`
- Participants: `POST /participants/enroll`, `POST /participants/consent`, `GET /participants/me`, `GET /participants/{id}/summary`, `POST /participants/survey`
- Tasks: `GET /tasks`, `POST /tasks/start`, `POST /tasks/complete`, `POST /tasks/abandon`
- Interactions: `POST /interactions/log`
- Access: `GET /access-check`

### Admin (`/api/admin`, admin role only)
`GET /participants`, `GET /participants/{id}/summary`, `GET /participants/{id}/interactions`, `GET /participants/{id}/timeline`, `GET /participants/{id}/analytics`, `GET /analytics/overview`, `GET /analytics/tasks`, `GET /analytics/surveys`, `GET /analytics/chatbot`, `GET /analytics/export`

### Dashboards (`/api/dashboards`, all authenticated users)
`sales/*` (KPIs, territories, revenue trend, category breakdown, sales reps), `production/*` (KPIs, inventory, margins, low stock, high-margin-low-stock), operations endpoints.

### Health
`GET /`, `GET /health`, `GET /api/v1/status`

## Setup

All commands run from the repo root via `make`.

```bash
# 1. Configure env
cp .env.example .env     # fill DATABASE_*, OPENAI_API_KEY, ANTHROPIC_API_KEY, JWT_SECRET_KEY

# 2. Prepare DB (PostgreSQL with pgvector + AdventureWorks loaded)
psql -U <user> -d Adventureworks -f backend/database/setup_database.sql

# 3. Install backend venv
make install-backend

# 4. Apply migrations + build schema embeddings
make migrate
make embed               # first-time only

# 5. Run
make dev-backend         # http://localhost:8000
```

Interactive API docs: `http://localhost:8000/docs`.

Direct alternative (no make): `cd backend && source venv/bin/activate && python main.py`.

## Key Concepts

- **Role-based access**: `get_current_user` FastAPI dependency injects `User`; endpoints check `user.can_access_chatbot()`, `user.can_access_dashboards()`, `user.can_access_admin()`.
- **Per-query token tracking**: every LLM call's usage is aggregated into `query_history.total_input_tokens`, `total_output_tokens`, `total_cost_usd`.
- **Multi-query iteration**: analyst can request a follow-up query; loop back to SQL Agent without re-orchestrating.
- **SQL retry with feedback**: validator issues feed back to the SQL Agent for up to 3 retries.
- **Schema filter optimization**: Validator uses only tables in `tables_used` from the SQL Agent, cutting validator token cost.
- **Anchor tables**: domain-specific tables always added to RAG results (sales, hr, production, purchasing).
- **IVFFlat workaround**: exclusions are filtered in Python after retrieval because the IVFFlat index does not play well with `WHERE` filters.

## Development

```bash
make test         # pytest
make lint         # ruff check
make format       # black + ruff --fix
```

## Environment Variables

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_HOST` / `PORT` / `NAME` / `USER` / `PASSWORD` | yes | AdventureWorks DB |
| `OPENAI_API_KEY` | yes | Embeddings |
| `ANTHROPIC_API_KEY` | yes | Claude |
| `JWT_SECRET_KEY` | yes | HS256 signing |
| `JWT_ALGORITHM` | no | default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | default `120` |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` | no | Cache |
| `LLM_MODEL` | no | Default Sonnet model id |
| `EMBEDDING_MODEL` | no | default `text-embedding-3-small` |
| `EMBEDDING_DIMENSIONS` | no | default `1536` |
| `TOP_K_TABLES` | no | default `5` |
| `ENABLE_ANCHOR_TABLES` | no | default `true` |
| `DEBUG` | no | reloads server |
| `API_HOST` / `API_PORT` | no | bind config |

## Related Docs

- [../README.md](../README.md): project overview, quick start, experiment framework
- [docs/workflow/](docs/workflow/): workflow diagrams (HTML, Mermaid, ASCII) and node reference
