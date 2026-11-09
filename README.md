# Isekai: A Life Unwritten

A single-player, text-based RPG set in an original anime-inspired dark fantasy world. Built as a one-session coding benchmark.

## Tech Stack

**Backend:**
- Python 3.12+
- FastAPI
- SQLAlchemy (async)
- SQLite (aiosqlite)
- Pydantic v2

**Frontend:**
- React 18 + TypeScript
- Vite
- Plain CSS (no UI libraries)

## Prerequisites

- Python 3.12 or higher
- Node.js 18+ and npm
- Git

## Installation

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Run database migrations (when available)
# alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Development Commands

### Backend

```bash
cd backend

# Start development server with auto-reload
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v

# Run linter
ruff check app/

# Format code
ruff format app/
```

### Frontend

```bash
cd frontend

# Start development server
npm run dev

# Type-check and build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm run test

# Lint code
npm run lint
```

## API Documentation

When the backend is running, API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Current Endpoints

- `GET /api/health` - Health check endpoint

## Project Structure

```
isekai-game/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI route handlers
│   │   ├── core/          # Config, database, RNG, exceptions
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── services/      # Game logic (authoritative)
│   │   └── main.py        # FastAPI app entry
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── screens/       # Page-level components
│   │   ├── context/       # React Context providers
│   │   ├── hooks/         # Custom hooks
│   │   ├── api/           # API client functions
│   │   ├── types/         # TypeScript types
│   │   ├── styles/        # Global CSS, variables
│   │   └── main.tsx       # Entry point
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
├── SPEC.md
├── AGENTS.md
└── README.md
```

## Architecture Notes

- **Backend is authoritative** - All game logic, calculations, and validation happen on the backend
- **Frontend is a dumb renderer** - Displays state, sends player actions, handles UI only
- **Database persistence** - SQLite file (`isekai.db`) in project root, survives browser refresh
- **Controlled RNG** - Seeded random number generator for reproducible gameplay
- **Modular monolith** - Separate service modules for each game system

## Environment Variables

### Backend (`.env`)
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///isekai.db` | SQLite database path |
| `API_HOST` | `0.0.0.0` | Server host |
| `API_PORT` | `8000` | Server port |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |

### Frontend (`.env`)
| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |

## Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm run test
```

## License

This project is a coding benchmark for educational purposes.