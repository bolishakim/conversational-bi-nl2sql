# Frontend: NL2SQL Thesis Experiment

Next.js 16 (App Router) frontend for the thesis experiment. Hosts the participant onboarding flow, BI dashboards, the conversational NL2SQL chatbot (experimental group only), the task completion interface, the post-study survey, and the admin analytics dashboard.

## Stack

- **Next.js 16** (App Router) + **React 19** + **TypeScript 5.9**
- **Tailwind CSS**
- **Plotly.js** (dashboard + chat result charts), **Recharts** (admin analytics)
- **SWR** for data fetching
- **lucide-react** icons
- **react-markdown** for task descriptions and chat analysis

## Ports

Dev: `http://localhost:3050`. Configure the backend URL via `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── app/                              App Router pages
│   ├── layout.tsx                    Root layout, wraps Providers
│   ├── page.tsx                      Landing (redirect to login or role home)
│   ├── login/                        Participant + admin login (email + password)
│   ├── onboarding/                   4-step participant flow: welcome → consent → pre-survey → success
│   ├── dashboards/
│   │   ├── sales/                    Revenue, territories, reps, category breakdown
│   │   ├── production/               Inventory, margins, low stock
│   │   └── operations/               Workforce, HR metrics
│   ├── chat/                         Chatbot interface (experimental group only)
│   │   └── history/                  Participant's past chat queries
│   ├── tasks/                        Task list
│   │   └── [taskId]/                 Task completion (answer + difficulty + confidence + markdown brief)
│   ├── survey/                       Post-study TAM-based survey
│   └── admin/                        Admin analytics (5 tabs)
│       └── participants/[id]/        Per-participant drilldown
│
├── components/
│   ├── Providers.tsx                 ChatProvider + TaskSessionProvider
│   ├── AuthenticatedLayout.tsx       Auth gate (calls /me, redirects to /login)
│   ├── Sidebar.tsx                   Role-aware navigation
│   ├── Header.tsx / Footer.tsx / Logo.tsx
│   ├── AuthForm.tsx                  Login form (captures Prolific params)
│   ├── TaskOverlay.tsx               Floating task widget shown during an active task
│   ├── ChatInput.tsx / MessageList.tsx / UserMessage.tsx / SystemMessage.tsx
│   ├── Button.tsx
│   ├── dashboards/                   Plotly chart wrappers + KPI cards
│   ├── admin/                        Admin tab components
│   └── workflow/                     Agent workflow visualization used in chat
│
├── contexts/
│   ├── ChatContext.tsx               Chat messages, SSE workflow state, abort controller
│   └── TaskSessionContext.tsx        Task list, current task, server-authoritative timer
│
├── lib/
│   ├── api.ts                        Fetch client, JWT + silent refresh (60s timer)
│   ├── auth.ts                       Token storage + expiry helpers
│   └── hooks/                        Shared hooks
│
├── types/
│   ├── auth.ts, experiment.ts, admin.ts
│   ├── message.ts, query.ts, history.ts, api.ts
│   └── index.ts
│
├── next.config.js
├── tailwind.config.ts
└── tsconfig.json
```

## Pages

| Route | Purpose | Access |
|-------|---------|--------|
| `/` | Landing; redirects by auth state and role | Public |
| `/login` | Email + password login; captures Prolific URL params | Public |
| `/onboarding` | Welcome + tutorial video, consent, pre-survey, success | Authenticated participant, pre-onboarded |
| `/dashboards/sales` | Revenue, territories, trends, category breakdown | All authenticated users |
| `/dashboards/production` | Inventory, margins, low stock | All authenticated users |
| `/dashboards/operations` | Workforce / HR | All authenticated users |
| `/chat` | Conversational NL2SQL with SSE streaming workflow viz | Experimental group only |
| `/chat/history` | Past chat queries for the current participant | Experimental group only |
| `/tasks` | Task list with completion status | Participants |
| `/tasks/[taskId]` | Task brief + answer + difficulty + confidence; draft persisted in sessionStorage | Participants |
| `/survey` | Post-study survey; redirects to Prolific completion code on submit | Participants who finished tasks |
| `/admin` | 5-tab analytics: overview, tasks, surveys, chatbot, export | Admin only |
| `/admin/participants/[id]` | Per-participant drilldown | Admin only |

## State + Providers

- **`ChatProvider`** (`contexts/ChatContext.tsx`): chat messages, SSE workflow node state, retry / iteration counters, abort controller. Scopes messages per participant (clears on participant switch).
- **`TaskSessionProvider`** (`contexts/TaskSessionContext.tsx`): task list (ordered by `task_number`), current task, elapsed timer derived from server-side `task_started_at`, helpers to start / complete / abandon tasks.

Both are mounted globally in `components/Providers.tsx`, itself wrapped in the root `app/layout.tsx`.

## Auth

- JWT stored in `localStorage` under `auth_token`.
- `APIClient` (`lib/api.ts`) runs a 60 s background timer that calls `/api/auth/refresh` when the token has under 10 minutes left.
- On any `401`, the client does one refresh + retry before redirecting to `/login`.
- `AuthenticatedLayout` calls `/api/auth/me` on mount to inject the user and enforce role gates.
- `Sidebar` renders a different nav tree for `admin`, `participant_control`, and `participant_experimental`; the chat section is locked (with an unlock icon) for control participants.

## Key Flows

### Onboarding
`choice → welcome (role-specific YouTube tutorial) → consent (3 checkboxes) → pre-survey (7 questions) → success (shows participant code + assigned condition)`. Calls `api.registerParticipant()`. Returning participants use `api.lookupParticipant()`.

### Chat (experimental group)
1. `/chat` calls `/api/auth/me`; rejects participants without `can_access_chatbot`.
2. `sendMessage` posts to `/api/chat/query/stream` (SSE) and updates the workflow graph live (node status per stage, retry/iteration counts).
3. On the final `result` event, extracts SQL, results table, Plotly chart config, analysis, token stats, and renders them in a `SystemMessage`.
4. `AbortController` cancels the previous query when a new one is sent.

### Task completion
1. `/tasks` lists tasks ordered by `task_number` (tutorial filtered out).
2. `/tasks/[taskId]` auto-starts the task (server stamps `task_started_at`). Timer is derived from that timestamp.
3. Answer, difficulty (1 to 5), and confidence (1 to 5) are persisted as drafts in `sessionStorage` keyed by `taskId` so a participant can navigate to dashboards / chat without losing progress.
4. Submit posts to `/api/experiment/tasks/complete`, clears draft, routes to next task or `/tasks` if all complete.
5. `TaskOverlay` shows a floating status widget on dashboards and chat while any task is active.

### Prolific integration
`AuthForm` captures `PROLIFIC_PID`, `STUDY_ID`, `SESSION_ID` from the URL and stashes them in `sessionStorage`. On post-survey submit, the app redirects to `https://app.prolific.com/submissions/complete?cc=<completion-code>`.

## Setup

From the repo root:

```bash
make install-frontend            # installs node_modules

# .env.local (in this directory)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local

make dev-frontend                # http://localhost:3050
```

Direct alternative (no make): `cd frontend && npm install && npm run dev`.

## Make targets (run from repo root)

| Target | Description |
|--------|-------------|
| `make install-frontend` | `npm install` |
| `make dev-frontend` | `npm run dev` on :3050 |
| `make build` | `npm run build` (production build) |
| `make start` | `npm run start` on :3050 (after `make build`) |
| `make lint` | `next lint` |
| `make clean-frontend` | Remove `node_modules` + `.next` + `tsconfig.tsbuildinfo` |

For running both backend + frontend together, use `make docker` (container stack) or two terminals with `make dev-backend` and `make dev-frontend`.

## Design

Minimal, functional, no decorative animation. Tailwind utility classes, Inter font, blue primary (`#3B82F6`), neutral gray surfaces. Participant condition is surfaced as a color-coded avatar badge (experimental: blue, control: orange, admin: purple).

## Related Docs

- [../README.md](../README.md): project overview and quick start
- [../backend/README.md](../backend/README.md): backend API, agent workflow, data model
- [../backend/docs/workflow/](../backend/docs/workflow/): workflow diagrams
