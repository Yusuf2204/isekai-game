# AGENTS.md — Isekai: A Life Unwritten

This document establishes the development rules, architecture, and conventions for the project. All agents working on this project must follow these guidelines.

---

## 1. Project Architecture & Technology Stack

### Backend
- **Language:** Python 3.12+
- **Framework:** FastAPI
- **ORM:** SQLAlchemy (async)
- **Database:** SQLite (file-based, `isekai.db`)
- **Validation:** Pydantic v2
- **Testing:** pytest + pytest-asyncio

### Frontend
- **Framework:** React 18+ with TypeScript
- **Build Tool:** Vite
- **Styling:** Plain CSS (no CSS-in-JS, no Tailwind, no UI libraries)
- **State Management:** React Context + useReducer (no Redux, no Zustand)
- **API Client:** Native `fetch` (no Axios, no TanStack Query)

### Project Structure
```
isekai-game/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI route handlers
│   │   ├── core/          # Config, database, RNG
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── services/      # Game logic (authoritative)
│   │   │   ├── character/
│   │   │   ├── world/
│   │   │   ├── game/
│   │   │   ├── events/
│   │   │   ├── combat/
│   │   │   ├── npc/
│   │   │   └── reincarnation/
│   │   └── main.py        # FastAPI app entry
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── screens/       # Page-level components (MainMenu, CharacterCreation, Gameplay, etc.)
│   │   ├── context/       # React Context providers
│   │   ├── hooks/         # Custom hooks
│   │   ├── api/           # API client functions
│   │   ├── types/         # TypeScript types matching Pydantic schemas
│   │   ├── styles/        # Global CSS, variables
│   │   └── main.tsx       # Entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── SPEC.md
├── AGENTS.md
└── README.md
```

---

## 2. Coding Conventions

### Python (Backend)
- **Style:** Ruff (line length 100, target version py312)
- **Type Hints:** Required on all public functions and class methods
- **Docstrings:** Google style for modules, classes, and public functions
- **Async:** Use `async`/`await` for all I/O (database, HTTP)
- **Error Handling:** Custom exception classes in `app/core/exceptions.py`; never bare `except:`
- **Imports:** Absolute imports from `app.` root; group stdlib, third-party, local

### TypeScript (Frontend)
- **Style:** ESLint + Prettier (single quotes, trailing commas, 2-space indent)
- **Strict Mode:** `strict: true` in tsconfig.json
- **Types:** Define interfaces matching backend Pydantic schemas in `src/types/`
- **Components:** Functional components with explicit `React.FC<Props>` typing
- **No `any`:** Use `unknown` or proper generics instead

### General
- **Git Commits:** Conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`)
- **Branch Naming:** `feature/short-description`, `fix/short-description`
- **No Magic Numbers:** Define constants in `app/core/constants.py` / `src/constants.ts`

---

## 3. Backend/Frontend Separation

### CRITICAL RULE: Game Logic is Authoritative on the Backend
- The backend **owns** all game state, calculations, and validation
- The frontend is a **dumb renderer** — it sends player intent, receives authoritative state
- **Never** implement game mechanics (combat math, event resolution, attribute checks, RNG) in the frontend
- **Never** trust client-provided values for health, money, skills, time, etc.
- Frontend responsibilities:
  - Display state from backend
  - Send player actions to backend
  - Handle loading/error UI states
  - Local UI animations/transitions only

### API Contract
- All communication via REST endpoints defined in `app/api/`
- Request/Response validated by Pydantic schemas in `app/schemas/`
- Frontend types in `src/types/` must mirror backend schemas exactly
- Use OpenAPI schema (`/openapi.json`) to verify contract alignment

---

## 4. Database Persistence Requirements

### SQLite Configuration
- Single file: `isekai.db` in project root (gitignored)
- SQLAlchemy async engine with `aiosqlite` driver
- Connection pool: `pool_size=5`, `max_overflow=10`
- **Migrations:** Alembic (configured but minimal — schema changes are rare in this scope)

### Required Tables (per SPEC §11.3)
| Table | Purpose |
|-------|---------|
| `game_sessions` | Session metadata, seed, current generation |
| `characters` | Per-life character data |
| `attributes` | Strength, Agility, Intelligence, Vitality, Luck |
| `skills` | Skill name, experience, level |
| `inventory` | Items, quantities |
| `npc_relationships` | NPC ID, relationship value, memory flags |
| `life_records` | Death records, legacy data |
| `gameplay_state` | Current location, time, day, active event |

### Persistence Rules
- **Every** player action that changes state must persist immediately
- Session must survive browser refresh (state loaded from DB on resume)
- Use database transactions for multi-table updates
- No in-memory global state that isn't backed by DB

---

## 5. Testing Expectations

### Backend (pytest)
- **Unit Tests:** All service modules (`services/`) — target 80%+ coverage
- **Integration Tests:** API endpoints with test database
- **Game Logic Tests:** Combat calculations, event resolution, attribute checks, RNG seeding
- **Fixtures:** `conftest.py` with test DB, seeded RNG, sample characters
- **Run:** `pytest backend/tests/ -v`

### Frontend
- **Component Tests:** React Testing Library for critical screens
- **Type Tests:** `tsc --noEmit` in CI
- **Manual Testing:** Required for all user-facing flows (playthrough)

### RNG Testing
- All randomness uses `app.core.rng.SeededRNG` (wraps `random.Random`)
- Tests must pass a fixed seed and assert deterministic outcomes
- Never use `random` module directly in game logic

---

## 6. Scope Restrictions (from SPEC §13)

### In Scope (Must Implement)
- 1 Kingdom (Eldoria), 3 Regions, 5–8 Locations
- 6 Playable Races, 5 Backgrounds
- 10–15 Important NPCs
- 20–30 Event Definitions
- 3–5 Enemy Types
- At least 2 Playable Generations per session
- All screens per SPEC §12
- Death & Reincarnation with limited legacy
- Session Summary

### Explicitly Out of Scope (Do Not Implement)
- Multiplayer, persistent online world, real-time simulation
- Autonomous NPC AI, LLM-powered GM
- Procedural infinite world, complex economy
- Large-scale politics, advanced crafting, complicated skill trees
- Voice acting, animation-heavy combat
- Authentication, user registration, payment systems
- Deployment infrastructure (Docker, K8s, cloud config)

### Do Not Expand Scope
- No additional frameworks, libraries, or infrastructure beyond SPEC §11.1
- No "nice to have" features not in acceptance criteria (§14)
- If unsure whether something is in scope, **ask before implementing**

---

## 7. Dependency Rules

### Avoid Unnecessary Dependencies
- **Backend:** Only `fastapi`, `uvicorn`, `sqlalchemy`, `aiosqlite`, `pydantic`, `pydantic-settings`, `python-multipart`, `alembic`, `pytest`, `pytest-asyncio`, `httpx`, `ruff`
- **Frontend:** Only `react`, `react-dom`, `typescript`, `vite`, `@vitejs/plugin-react`, `eslint`, `prettier`, `@testing-library/react`, `@testing-library/jest-dom`, `jest`, `ts-jest`
- **No:** ORMs other than SQLAlchemy, state libraries (Redux, Zustand), UI libraries (MUI, Chakra, shadcn), animation libraries, date libraries (use native), axios, tanstack-query, zod, class-validator, etc.

### Version Pinning
- Pin exact versions in `requirements.txt` and `package.json`
- No `^` or `~` version ranges

---

## 8. Preserve Existing Working Code

- **Never** rewrite working code without a clear reason (bug fix, spec change, performance)
- **Never** delete tests that pass — update them if behavior changes intentionally
- **Never** change database schema without a migration
- **Never** modify SPEC.md or AGENTS.md without explicit user approval
- When refactoring, run full test suite before and after

---

## 9. Incremental Feature Implementation

### Build in Working Vertical Slices
Each increment must be **playable end-to-end** for its scope:

| Increment | Deliverable |
|-----------|-------------|
| 1 | Project scaffold, DB, API health check, basic React app |
| 2 | Character generation (race, background, attributes), New Game flow |
| 3 | World/locations, time system, basic activities (explore, rest, work) |
| 4 | Event system with choices and consequences |
| 5 | NPCs, relationships, dialogue |
| 6 | Combat system |
| 7 | Death, life record, reincarnation, legacy |
| 8 | Session summary, polish, bug fixes |

### Rules for Each Increment
- Backend API complete and tested before frontend integration
- Frontend screen functional with real API calls (no mocks in final code)
- Manual playtest at each increment
- Commit early, commit often — each increment on its own branch

---

## 10. RNG & Determinism

- Single source of randomness: `app.core.rng.get_rng(session_seed: int) -> SeededRNG`
- Seed generated at session creation, stored in `game_sessions.seed`
- All game logic (generation, events, combat, loot) uses this RNG
- **No** `random.random()`, `random.randint()`, `numpy`, `secrets` in game logic
- Frontend never generates randomness for game mechanics

---

## 11. Error Handling & Logging

### Backend
- Structured logging: `structlog` (JSON output)
- Custom exceptions: `GameError`, `ValidationError`, `NotFoundError`, `ConflictError`
- Global exception handler returns consistent JSON: `{ "error": "code", "message": "...", "details": {} }`
- HTTP status codes: 400 (client), 404 (missing), 409 (state conflict), 500 (server)

### Frontend
- Global error boundary for React crashes
- API error handling hook: `useApiError()` → shows toast/banner
- Loading states for all async actions

---

## 12. Configuration

### Backend (`app/core/config.py` via `pydantic-settings`)
- `DATABASE_URL` (default: `sqlite+aiosqlite:///isekai.db`)
- `API_HOST`, `API_PORT`
- `CORS_ORIGINS` (default: `http://localhost:5173`)
- `LOG_LEVEL`

### Frontend (`vite.config.ts` + `.env`)
- `VITE_API_URL` (default: `http://localhost:8000`)

---

## 13. Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest tests/ -v

# Frontend
cd frontend
npm install
npm run dev        # Vite dev server on :5173
npm run build      # Type-check + build
npm run test       # Jest + RTL
npm run lint       # ESLint + Prettier check
```

---

## 14. Specification Conflicts & Ambiguities (Identified)

| # | Area | Issue | Recommended Resolution |
|---|------|-------|------------------------|
| 1 | §5.3 Attributes | "Simple numerical scale" undefined | Use 1–20 base + racial modifiers (total 1–25) |
| 2 | §6.2 Time | No day/week/month tracking specified | Add `day_count` integer; time periods cycle daily |
| 3 | §6.3 Activities | "Work", "Trade", "Train" details unspecified | Define as: Work → money + time; Trade → buy/sell; Train → skill XP + time |
| 4 | §7 NPCs | "Basic dialogue" & "Memory of decisions" vague | Dialogue: 3–5 lines per NPC; Memory: boolean flags per key decision |
| 5 | §8 Combat | "Lightweight turn-based" — no initiative system | Initiative = Agility + 1d20; simple action economy |
| 6 | §9.3 Legacy | "Limited legacy" — no concrete limits | Max 1 legacy trait per life: +1 attribute, or skill affinity, or minor bonus |
| 7 | §11.2 Modules | Suggested modules vs. actual implementation | Follow suggested module names; combine `game` + `events` if simple |
| 8 | §12 UI | "Responsive on mobile" — no breakpoint spec | Mobile-first CSS; breakpoints at 640px, 1024px |
| 9 | §14 Acceptance | "No critical runtime errors" — subjective | Define: no 500 errors, no unhandled promise rejections, no data loss on refresh |

**Action Required:** User approval needed on recommended resolutions before implementation begins.

---

## 15. Final Reminders

1. **Read SPEC.md first** — every implementation decision traces to it
2. **Backend is authoritative** — frontend never calculates game mechanics
3. **Persist everything** — session survives refresh
4. **Test game logic** — RNG-seeded, deterministic, verifiable
5. **Scope is fixed** — no additions without approval
6. **Incremental delivery** — working vertical slices only
7. **Ask when ambiguous** — don't guess on SPEC conflicts

---

*This document is binding for all agents. Update only with explicit user approval.*