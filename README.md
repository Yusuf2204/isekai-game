# Isekai: A Life Unwritten

A single-player, text-based RPG set in an original anime-inspired dark fantasy world. Built as an authoritative-backend coding benchmark.

---

## Tech Stack

### Backend
- **Language & Runtime:** Python 3.12+
- **Web Framework:** FastAPI
- **ORM:** SQLAlchemy (asyncio)
- **Database:** SQLite via `aiosqlite`
- **Validation:** Pydantic v2 & `pydantic-settings`
- **Migrations:** Alembic (async configuration)
- **Testing:** `pytest` + `pytest-asyncio` + `httpx`
- **Linter & Formatter:** Ruff (strict py312)
- **Logging:** Structured logging (`app.core.logging`) with standard/JSON formatters

### Frontend
- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite
- **Styling:** Plain CSS with CSS Custom Properties (Dark Fantasy theme, no Tailwind, no CSS-in-JS, no UI libraries)
- **State Management:** React Context + `useReducer`
- **HTTP Client:** Native `fetch` with typed `ApiClient` and `ApiClientError`
- **Testing:** Jest + `ts-jest` + jsdom

---

## Prerequisites

- Python 3.12 or higher
- Node.js 18+ and npm
- Git

---

## Installation & Setup

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Database initialization & migrations:
# The database schema and static world data (Kingdom, Regions, Locations, Races,
# Backgrounds, and Enemies) are initialized and seeded automatically at startup.
# Alembic is configured for optional schema migration management:
# alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

The backend API will be available at `http://localhost:8000`.

### 2. Frontend Setup

```bash
cd frontend

# Install exact pinned dependencies
npm install

# Configure environment variables
cp .env.example .env

# Start development server
npm run dev
```

The frontend application will be available at `http://localhost:5173`.

---

## Development Commands

### Backend

```bash
cd backend

# Run development server
uvicorn app.main:app --reload --port 8000

# Run full test suite (isolated test DB)
pytest tests/ -v

# Run targeted test file
pytest tests/test_stage7_startup_seeding.py -v

# Run linter
ruff check app/ tests/

# Run formatter check
ruff format --check app/ tests/

# Alembic migrations (when modifying SQLAlchemy models)
alembic current
alembic heads
alembic revision --autogenerate -m "describe_changes"
alembic upgrade head
```

### Frontend

```bash
cd frontend

# Start Vite dev server on :5173
npm run dev

# Run TypeScript type-check and Vite production build
npm run build

# Preview production build
npm run preview

# Run Jest unit and smoke tests
npm run test

# Run ESLint on src/
npm run lint
```

---

## API Documentation & Endpoints

When the backend is running, interactive documentation is available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

### Implemented Endpoints

#### System & Health
- `GET /api/health` — System status, service identity, and version.

#### Character
- `POST /api/character/create` — Create character (generates random identity, race/background attributes, starting skills, starting inventory, and session token).
- `GET /api/character/current` — Get active character data.
- `GET /api/character/attributes` — Get attributes and attribute experience.
- `GET /api/character/skills` — Get skills, skill experience, and levels.
- `GET /api/character/resources` — Get health, stamina, fatigue, and effective resource caps.
- `GET /api/character/progression` — Unified progression overview.

#### World & Locations
- `GET /api/world/kingdom` — Kingdom details (Eldoria).
- `GET /api/world/regions` — List all regions.
- `GET /api/world/locations` — List locations (supports optional `region_id` query).
- `GET /api/world/locations/current` — Current character location.
- `POST /api/world/locations/travel` — Travel to an adjacent location (advances time and ticks daily conditions).

#### Time
- `GET /api/time/periods` — List time periods; reports real `current_period` when `session_token` query is provided.
- `POST /api/time/advance` — Advance time period (ticks daily conditions once per elapsed day).

#### Activities
- `POST /api/activities/explore` — Explore current location (spends time, consumes stamina, yields discovery/rewards).
- `POST /api/activities/rest` — Rest to recover health and stamina (spends time; handles interrupted rest).
- `POST /api/activities/work` — Work at current location (spends time, consumes stamina, earns money).

#### Conditions & Treatments
- `GET /api/conditions/` — List active conditions for character.
- `GET /api/conditions/definitions` — Catalog of condition definitions and effects.
- `GET /api/conditions/treatments` — Catalog of all treatment definitions.
- `GET /api/conditions/{condition_id}/treatments` — Available treatments for a specific active condition.
- `POST /api/conditions/treat` — Apply treatment to reduce or cure a condition.

#### Inventory
- `GET /api/inventory/` — Character inventory items and quantities.
- `POST /api/inventory/use` — Consume/use an item (validates and consumes by `item_id`).

---

## Architecture & Conventions

1. **Backend Authoritative:** All game rules, calculations, attribute checks, and RNG occur on the backend. The frontend is a dumb renderer that reflects state and sends player intent.
2. **Deterministic RNG:** All randomness is powered by `app.core.rng.SeededRNG` wrapping session seeds (`game_sessions.seed`). Logic never uses raw unseeded random functions.
3. **Database & Transactions:**
   - Single-file SQLite database (`isekai.db`) in project root.
   - Transaction boundaries are owned by the composition root (`get_session()` / `get_db_session()`); domain services only flush.
   - Application startup (`lifespan`) executes idempotent world seeding inside one composition-root transaction, ensuring fresh installations are immediately playable without manual setup.
   - SQLite with `aiosqlite` uses standard file locking; connection pool parameters (`pool_size`, `max_overflow`) are not applicable to file-based SQLite and are omitted in engine configuration.
4. **Error Handling & Envelope:**
   - Standard error envelope across all endpoints:
     ```json
     {
       "error": "ERROR_CODE",
       "message": "Human-readable description",
       "details": {}
     }
     ```
   - Handled globally by `app.core.errors.register_error_handlers`.
5. **Frontend Error Boundary & Plain CSS:**
   - Root application is wrapped with `ErrorBoundary` catching unhandled React render crashes.
   - Strict Plain CSS styling with CSS custom properties in `variables.css` and semantic classes in `main.css`. Zero Tailwind or UI framework classes.

---

## Environment Variables

### Backend (`.env`)
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///isekai.db` | SQLite database connection string |
| `API_HOST` | `0.0.0.0` | Server bind host |
| `API_PORT` | `8000` | Server bind port |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Application log level (DEBUG, INFO, WARNING, ERROR) |

### Frontend (`.env`)
| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |

---

## Testing Verification

### Backend Tests
```bash
cd backend
pytest tests/ -v
# Status: 314 passed
```

### Frontend Tests
```bash
cd frontend
npm run test
# Status: 9 passed
```

---

## Project Structure

```
isekai-game/
├── backend/
│   ├── alembic/           # Alembic migration environment (async)
│   ├── alembic.ini        # Alembic configuration
│   ├── app/
│   │   ├── api/           # FastAPI route handlers
│   │   ├── core/          # Config, database, RNG, errors, logging, constants
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic request & response models
│   │   ├── services/      # Game domain logic (authoritative)
│   │   └── main.py        # FastAPI app entry point & lifespan
│   ├── tests/             # Automated test suite (isolated test DB)
│   ├── requirements.txt   # Exact pinned Python dependencies
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/           # Typed API client
│   │   ├── components/    # Reusable UI components & ErrorBoundary
│   │   ├── hooks/         # Custom React hooks (useApiError)
│   │   ├── styles/        # Plain CSS stylesheets & variables
│   │   ├── types/         # TypeScript interfaces matching backend schemas
│   │   ├── constants.ts   # Frontend constants & API endpoint map
│   │   ├── App.tsx        # Main application component
│   │   └── main.tsx       # Vite entry point
│   ├── jest.config.cjs    # Jest configuration
│   ├── package.json       # Exact pinned npm dependencies
│   ├── vite.config.ts     # Vite configuration with proxy to :8000
│   └── .env.example
├── SPEC.md                # Game design and specification
├── AGENTS.md              # Technical guidelines & architecture rules
├── ROADMAP.md             # Living progress tracking & audit status
└── README.md              # Project overview and instructions
```

---

## License

This project is a coding benchmark for educational purposes.
