# ROADMAP.md — Isekai: A Life Unwritten

> **Living progress document.** This file tracks what has been built, what has
> been verified, what is still broken, and what remains. It is **not** a
> replacement for `SPEC.md` (product specification) or `AGENTS.md` (working
> rules). When this file conflicts with those documents, `SPEC.md` and
> `AGENTS.md` win.
>
> **Source of truth for findings:** the audit recorded in the project history.
> Findings listed here were **not independently re-audited** during the creation
> of this roadmap. Treat them as *reported* unless a remediation stage verifies
> them.

---

## A. Project Overview

- **Project name:** Isekai: A Life Unwritten
- **Description:** A single-player, text-based anime isekai / dark fantasy RPG.
  The player is reincarnated as an ordinary person, lives a life with
  consequences, dies, and may reincarnate with a limited legacy.
- **Final objective:** Deliver a functional, playable, single-session RPG where
  the player can create a character, act in the world, make consequential
  choices, die, reincarnate, and view a session summary. Target duration
  15–30 minutes, at least two playable generations per session.
- **Primary technologies:**
  - Backend: Python 3.12+, FastAPI, SQLAlchemy (async), SQLite/aiosqlite,
    Pydantic v2, Alembic, pytest.
  - Frontend: React 18 + TypeScript, Vite, plain CSS.
- **References:**
  - `SPEC.md` — specification, scope, acceptance criteria.
  - `AGENTS.md` — architecture, conventions, dependency and testing rules.
  - `README.md` — setup and development commands (partially stale; see Stage 9).

---

## B. Development Status

> No overall percentage is given. Progress is tracked by phase and stage status,
> not by an unmeasured completion ratio.

| Area | Status | Summary |
|------|--------|---------|
| Backend foundation | COMPLETED | FastAPI app, async SQLAlchemy engine/session, models, schemas, config, routers, global error handlers, startup seeding, async Alembic migrations, structured logging, shared constants. |
| Core gameplay systems | PARTIAL | Character creation, progression, resources, conditions, time, world locations, activities, inventory/treatment, and event system. NPC, combat, death/legacy, reincarnation, session summary not implemented. |
| Incomplete gameplay features (Stage 10) | IN PROGRESS | Increment 1 (Event system) COMPLETED / VERIFIED. Increments 2–8 pending approval. |
| Backend reliability and remediation | COMPLETED | Stages 0, 1, 2, 3, 4, 5, 6, 7, 8, and 9 completed and verified. Stage 10 next. |
| Frontend | PARTIAL | React 18 + TS Vite scaffold, plain CSS styles, API client with error handling, ErrorBoundary, useApiError hook, and health screen. Screens for character creation and gameplay pending Stage 10. |
| Gameplay completeness | PARTIAL | No complete end-to-end gameplay loop yet (no events, combat, death, reincarnation, or session summary). |
| Integration and acceptance testing | PARTIAL | Full backend suite passes (314 passed); frontend smoke test passes (9 passed). Acceptance criteria in `SPEC.md` §14 demonstrated incrementally. |

---

## Status Convention

| Status | Meaning |
|--------|---------|
| `NOT STARTED` | No work done. |
| `PLANNED` | Scoped and scheduled, implementation not started. |
| `IN PROGRESS` | Work currently underway. |
| `IMPLEMENTED` | Code/changes exist. |
| `TESTED` | Relevant tests were run and passed. |
| `VERIFIED` | Result checked against acceptance criteria. |
| `PARTIAL` | Only part of the scope is complete. |
| `BLOCKED` | Cannot proceed due to a dependency or issue. |
| `CLOSED` | Reported finding was remediated and verified. |
| `DEFERRED` | Scoped but intentionally moved to a later stage. |
| `NOT VERIFIED` | Implemented or reported, but not independently confirmed. |

`IMPLEMENTED` does **not** imply `TESTED` or `VERIFIED`. A phase may hold several
statuses for different subtasks.

---

## C. Completed Development Phases

> The phases below are recorded as implemented from project history. Unless a
> phase explicitly says `TESTED`/`VERIFIED`, its behavior has **not** been
> independently verified during this roadmap update. The full backend suite was
> run during Stage 1 and again after Stage 3B/3C; see §G.

| Phase | Description | Status |
|-------|-------------|--------|
| **PART 0 — Specification and agent guidelines** | `SPEC.md` (product spec, scope, acceptance criteria) and `AGENTS.md` (architecture, conventions, dependencies, testing rules) exist. | IMPLEMENTED |
| **PART 1 — Project foundation** | Backend FastAPI app, health endpoint, config, async DB engine/session, React + Vite scaffold, initial health UI. | IMPLEMENTED / PARTIAL (frontend is health-only) / NOT VERIFIED |
| **PART 2 — Database and world foundation** | SQLAlchemy models for sessions, characters, attributes, skills, inventory, NPC relationships, life records, legacy, gameplay state, kingdom/regions/locations/races/backgrounds/enemies. Seed data for Eldoria, 3 regions, 7 locations, 6 races, 5 backgrounds, enemies. | IMPLEMENTED / PARTIAL (startup seeding not wired; Orphan seed skill corrected in Stage 1) / NOT VERIFIED |
| **PART 3A — Character creation foundation** | Character creation service, schemas, endpoint, random identity generation, racial modifiers, backgrounds, personality, starting skills/location, session token. | IMPLEMENTED / PARTIAL (Stage 1 deterministic RNG and seed validation verified; broader phase not fully verified) |
| **PART 3B — Character initialization** | Initial money, health/resources, inventory, starting skills, game session and gameplay state initialization. | IMPLEMENTED / NOT VERIFIED |
| **PART 3C — World, time, and basic activities** | Location/world API, time API and periods, activities (explore, work, rest, train, socialize, trade), travel, activity log. | IMPLEMENTED / PARTIAL (time API alignment pending) / NOT VERIFIED |
| **PART 3D — Character progression** | Attribute points, attribute experience, skill experience/levels, unified progression status. | IMPLEMENTED / NOT VERIFIED |
| **PART 3E.1 — Health and resources** | Health/stamina/fatigue status, health changes, stamina/fatigue penalties and resource endpoints. | IMPLEMENTED / PARTIAL (duplicate health validator; stamina percentage bounds) / NOT VERIFIED |
| **PART 3E.2 — Stamina, fatigue, and conditions** | Condition model (severity, duration), condition effects, fatigue, stamina penalties, treatment scaffolding. | IMPLEMENTED / PARTIAL (zero-value handling, effective stamina, debug block bug) / NOT VERIFIED |
| **PART 3E.3-R2 — Money, inventory, and treatment atomicity** | Money changes, inventory add/remove/use, treatments, transaction-oriented revisions. | IMPLEMENTED / PARTIAL (item identity mismatch; duplicate condition/treatment routes) / TRANSACTION OWNERSHIP VERIFIED |

---

## D. Audit and Remediation Roadmap

> **No stage below is approved for implementation by default.** Stages 2–10 are
> `PLANNED` unless explicitly stated otherwise. Each stage requires separate
> approval before code changes, and must not be bundled with large feature work.

### D0. Approved Plan Audit and Architecture Anchor

- **Status:** APPROVED — 2026-11-11. No implementation started.
- **Scope:** Audit of Stages 2–10 against the current backend structure. Findings
  below are recorded; only mappings/statuses with direct evidence were changed.
- **Anchor rules:**
  1. **Transaction boundary:** `get_db_session()` / `get_session()` owns request
     commit and rollback. Domain services flush only. API endpoints do not
     commit. Startup seeding and maintenance scripts own explicit transactions
     at the composition root.
  2. **Game context:** one resolver loads `game_session`, the current
     `Character`, and `GameplayState`; endpoints do not duplicate this lookup.
  3. **Authoritative time:** `app/services/game/time.py` is the only time engine.
     `app/services/world/locations.py` delegates to it. Conditions tick exactly
     once per elapsed day.
  4. **Domain ownership:** each domain service owns its rules, raises custom
     exceptions, and returns domain data. HTTP mapping belongs to the API/error
     boundary.
  5. **Error boundary:** global handlers in `app/main.py` produce one error
     envelope; endpoint `try/except` duplication is removed where possible.
  6. **Test boundary:** each test gets isolated state; order-dependent tests are
     not acceptable evidence.
  7. **Feature slices:** Stage 10 features are implemented one increment at a
     time with separate approval and acceptance checks.
- **Plan corrections:**
  - Stage 2 covers API commits as well as service commits; startup seeding is
    the documented exception.
  - TD-03 is a Stage 2 gate, not deferred cleanup.
  - Stage 3 must delete or delegate the duplicate `advance_time`.
  - Stage 4 must verify condition effects remain in the request transaction
    after Stage 2 removed the service commit.
  - Stage 5 must choose one canonical condition/treatment route and one
    `TreatmentRequest` schema before coding.
  - Stage 6 is safest after Stage 2, because both touch endpoint error flow.
  - Stage 7 depends on Stage 2 for the startup transaction boundary.
  - TD-01/TD-02 move to Stage 9 as quality gates.
  - PR-10 is deferred to Stage 4 as part of activity RNG/resource correctness.
  - Stage 10 must not bundle increments.

### STAGE 0 — Database Safety

| Subtask | Status | Notes |
|---------|--------|-------|
| **0A — Backup and hash verification** | COMPLETED | Development DB backed up outside the active DB directory; SHA-256 verified identical. |
| **0B — Test database isolation** | COMPLETED | `backend/conftest.py`, `backend/pytest.ini`, path-based `recreate_db()` guard, `.gitignore`, and a canary test. Canary: 4 passed. Full suite not run. |
| **0C — Additional verification** | NOT REQUIRED AS A SEPARATE STAGE | Canary verification was performed during 0B. Full-suite verification was completed during Stage 1. |

- **Stage 0A record:** source `backend/isekai.db`, 290,816 bytes, SHA-256
  `5c746a7a0611b3af21bae1398a68546b2dcb0868b381bc7d42bef06881903824`.
  Backup: `/tmp/opencode/isekai-db-backups/isekai.db.bak.20261109T162523466960865Z.2324868`.
- **Stage 0B record:** tests use `backend/test_isekai.db`; `recreate_db()` refuses
  any path other than the resolved `backend/test_isekai.db`; development DB hash
  unchanged after the canary run.

### STAGE 1 — Deterministic RNG and Seed Validation

- **Status:** COMPLETED / VERIFIED.
- **Tasks:**
  - Use the seeded RNG (`app.core.rng`) for personality generation.
  - Validate seed skill names against the skill enum.
  - Handle invalid seed skills without silent failure.
- **Dependencies:** Stage 0B.
- **Acceptance:** no uncontrolled `random` use in game logic; same seed yields
  deterministic results; invalid seed data fails loudly or is corrected.
- **Implementation record:**
  - Personality selection now uses `get_rng(game_session.seed)`; the global
    `random` module is no longer used for game logic.
  - Background starting skills are validated at seed time and character creation
    time. Invalid names raise `ValidationError` instead of being silently dropped.
  - Orphan starting skills corrected to
    `{"survival": 2, "negotiation": 1}` (previously included invalid `stealth`).
  - Added `backend/tests/test_stage1_rng_and_skills.py` (12 tests).
  - Legacy test setup repaired for `test_activities_api.py` and
    `test_skill_progression.py` using function-scoped autouse fixtures.
- **Verification record:**
  - `test_activities_api.py`: 22 passed.
  - `test_skill_progression.py`: 17 passed.
  - Both files together: 39 passed.
  - Full suite `pytest tests/ -v`: **263 passed**.
  - Orphan creation verified against `backend/test_isekai.db`: starting skills
    are `survival` and `negotiation`.
- **Development database repair record:**
  - Pre-repair backup:
    `/tmp/opencode/isekai-db-backups/isekai.db.bak.20261111T083905207573128Z`
    (290,816 bytes, verified with `cmp`).
  - Pre-repair SHA-256:
    `5c746a7a0611b3af21bae1398a68546b2dcb0868b381bc7d42bef06881903824`.
  - Repair: ran `seed_world()` once directly on `backend/isekai.db`; no
    `recreate_db()`, no schema changes, no character data existed to modify.
  - Only `backgrounds.id=3` (ORPHAN) changed:
    `starting_skills` `{"survival": 2, "stealth": 1}` →
    `{"survival": 2, "negotiation": 1}`, plus its `updated_at`.
  - Post-repair SHA-256:
    `6f75dfd7201f6fd370b6ab241832bc15cb0bf672dfda7fe77a4940343e369c2f`
    (290,816 bytes).
  - Foreign-key check passed; database opens and reads normally.

### STAGE 2 — Transaction Ownership

- **Status:** COMPLETED / VERIFIED.
- **Dependencies:** Stage 0B; TD-03 gate (closed in 2A).
- **Task list:**

| Subtask | Status | Notes |
|---------|--------|-------|
| **2A — Test isolation gate** | COMPLETED | Added function-scoped autouse DB fixtures to `test_time_api.py` and `test_character_progression.py`; both pass standalone. TD-03 closed. |
| **2B — Commit inventory** | COMPLETED | Inventoried all app commit sites: `creation.py`, `activities.py` (3), `locations.py`, `seed.py`, `api/time.py`, and `api/inventory.py` (2). Only `core/database.py` retains the boundary commit. |
| **2C — Remove service commits** | COMPLETED | Replaced service commits with `flush()` in character creation, explore/rest/work, travel, and `seed_world()`. |
| **2D — Remove API commits** | COMPLETED | Removed commits from time advance and inventory use/treat endpoints; `get_db_session()` now owns request commits. |
| **2E — Preserve composition-root transactions** | COMPLETED | Documented caller-owned transactions in `get_session()` and `seed_world()`. No startup seeding exists yet; Stage 7 must use the same boundary. |
| **2F — Regression tests** | COMPLETED | Added `tests/test_transaction_ownership.py`: multi-table persistence, rollback, seed atomicity, and source-level absence of service/API commits. |
| **2G — Verification and record** | COMPLETED | Targeted transaction tests 4 passed; affected API/service tests 119 passed; full suite 267 passed. Ruff has only pre-existing Stage 9 debt; dev DB hash unchanged. |

- **Implementation order:** 2A → 2B → 2C/2D → 2E → 2F → 2G.
- **2A verification record:** baseline standalone failures were 6 in
  `test_time_api.py` and 14 in `test_character_progression.py`. After adding
  function-scoped autouse fixtures, the files pass standalone (7 and 14), pass
  together (21), and the full suite passes (263). Ruff check/format pass on both
  files; development DB hash is unchanged.
- **Stage 2 verification record:** `test_transaction_ownership.py` 4 passed;
  affected character/world/activity/time/condition tests 119 passed; full suite
  267 passed with 248 warnings. A dedicated Stage 1 + Stage 2 confirmation rerun
  passed 16 tests (`test_stage1_rng_and_skills.py` 12,
  `test_transaction_ownership.py` 4). `ruff check` still reports only the 22
  pre-existing Stage 9 errors, including 7 in Stage 2-touched inventory/activity
  files; `ruff format --check` still flags pre-existing `inventory.py` formatting.
  Development DB hash remained
  `6f75dfd7201f6fd370b6ab241832bc15cb0bf672dfda7fe77a4940343e369c2f`.
- **Acceptance:** multi-table operations remain atomic; no partial writes on
  failure; no service-level or endpoint-level commit; TD-03 is closed; full
  suite passes with the development database hash unchanged.

### STAGE 3 — Authoritative Time System

- **Status:** COMPLETED / VERIFIED.
- **Approved decisions:**
  - `app/services/game/time.py` is the only authoritative time engine.
  - CB-18: `/api/time/periods` accepts optional `session_token`; when supplied,
    it returns the real `current_period`; when absent, `current_period` is
    `null`.
  - PR-12: `AdvanceTimeResponse` gains `days_advanced` and
    `expired_conditions`.
  - Keep the engine's `time_advance` log; travel/activity callers may add a
    second log entry. Revisit only if too noisy.
- **Tasks:**
  - [x] **3A — Regression tests:** Add failing tests for condition ticking
    across time API, activities, and travel; assert a single `advance_time`
    implementation and no `world_advance_time` caller.
  - [x] **3B — Consolidate engine:** Deleted the duplicate `advance_time` from
    `world/locations.py`; travel delegates to `game.time.advance_time`; removed
    the duplicate export from `world/__init__.py`.
  - [x] **3C — Activities:** Explore/rest/work use the authoritative engine;
    removed the `world_advance_time` import. This was completed with 3B because
    removing the world export would otherwise create a circular import.
  - [x] **3D — API alignment:** Added PR-12 response fields (`days_advanced`,
    `expired_conditions`) to `AdvanceTimeResponse`; implemented CB-18 optional
    session-token period reporting (returns `current_period` when provided, `null`
    when absent; handles missing session with 404).
  - [x] **3E — Verification:** Run targeted time/activity/world tests (17 passed),
    then the full suite (277 passed); confirm the development DB hash is unchanged.
  - [x] **3F — Documentation:** Record verification, close CB-18 and PR-12, and
    update this roadmap.
- **Out of scope:** calendar/week/month/year tracking, real-time clocks,
  event/NPC scheduling, activity or travel cost changes, Stage 4 condition/resource
  math, Stage 5 inventory/treatment routes, Stage 6 error handling, Stage 7
  startup seeding, frontend work, schema changes, migrations, new dependencies,
  and Stage 9 lint cleanup.
- **Dependencies:** Stage 2.
- **Acceptance:** one time-advancement path; conditions tick exactly once per
  elapsed day across all paths; travel and activities produce identical time
  semantics for the same elapsed periods.
- **3A verification:** `pytest tests/test_stage3_time_authority.py -v` produced
  6 expected failures and 2 passing baseline tests. Failures prove the duplicate
  engine, `world_advance_time` callers, and missing condition ticks on
  explore/rest/work/travel. The time API baseline and same-day no-tick guard
  pass.
- **3B/3C verification:** `test_stage3_time_authority.py` now passes 8/8;
  targeted time/activity/world/condition tests pass 90/90.
- **3D/3E/3F verification:** Added test coverage for `GET /api/time/periods` with
  session token (valid, after advancement, and invalid token 404) and PR-12
  response fields in `test_time_api.py` (9/9 passed). Stage 3 test files pass
  17/17 (`test_stage3_time_authority.py` 8, `test_time_api.py` 9). Full suite passes
  277/277 with 256 warnings. Development DB hash remains
  `6f75dfd7201f6fd370b6ab241832bc15cb0bf672dfda7fe77a4940343e369c2f`.
  CB-07, CB-18, and PR-12 are closed.

### STAGE 4 — Resource and Condition Mathematics

- **Status:** COMPLETED / VERIFIED.
- **Tasks:**
  - [x] Correct health change calculations (including interrupted rest) (CB-10).
  - [x] Make effective stamina consistent across validation and display (CB-15).
  - [x] Clamp stamina, health, and fatigue percentages to valid bounds (CB-14).
  - [x] Validate `severity` and `duration` correctly, including zero values and negative checks (CB-13).
  - [x] Consolidate duplicate health-bound validators into one shared implementation (CB-11).
  - [x] Verify condition effects remain in the request transaction after Stage 2; do not reintroduce commits inside activity services (CB-16).
  - [x] Clarify activity RNG seed fallback semantics (`rng_seed if rng_seed is not None else ...`) as part of activity correctness (PR-10).
  - [x] Remove or repair related dead code and debug blocks (CB-12).
- **Dependencies:** Stages 2, 3.
- **Acceptance:** reported resource changes match persisted state; no double
  penalties; validators have a single implementation; condition effects persist
  in the same transaction as the activity that caused them.
- **Verification record:**
  - Added `backend/tests/test_stage4_resource_math.py` with 9 targeted regression
    tests (9/9 passed).
  - Tested interrupted rest health delta calculation, single shared
    `validate_health_bounds` definition, severity/duration zero overrides and
    negative rejection, stamina percentage clamp at 100%, effective stamina
    validation in activities, and deterministic RNG seed fallback with seed 0.
  - Affected condition/resource/activity test suites pass 124/124.
  - Full test suite `pytest tests/ -q` passes **286 passed**, 264 warnings.
  - Pre-existing Ruff errors reduced from 22 to 13.
  - Development DB hash remains
    `6f75dfd7201f6fd370b6ab241832bc15cb0bf672dfda7fe77a4940343e369c2f`.
  - Findings CB-10, CB-11, CB-12, CB-13, CB-14, CB-15, and PR-10 are closed.

### STAGE 5 — Inventory and Treatment Consolidation

- **Status:** COMPLETED / VERIFIED.
- **Tasks:**
  - [x] Choose and document one canonical route namespace for condition/treatment operations (`/api/conditions`); remove duplicate route family from `/api/character` (CB-19).
  - [x] Make item identity consistent (`item_id` authoritative) for validation and consumption in `use_item_endpoint` (CB-05).
  - [x] Consolidate `TreatmentRequest` and `TreatmentResponse` schemas into shared schemas in `app/schemas/conditions.py` (CB-19).
  - [x] Fix local variable shadowing collision on `has_item` in `get_available_treatments_for_condition` (CB-19 / F823).
  - [x] Add targeted integration tests in `backend/tests/test_stage5_inventory_consolidation.py` (11 passed).
  - [x] Resolve all 13 project Ruff lint errors; achieve 0 Ruff lint errors across entire codebase.
- **Dependencies:** Stages 2, 4.
- **Acceptance:** one contract per inventory/treatment operation; no item identity mismatch; duplicate routes and schemas are removed; integration tests exist.
- **Verification record:**
  - Added `backend/tests/test_stage5_inventory_consolidation.py` with 11 integration tests (11/11 passed).
  - Tested `use_item` authoritative consumption by `item_id`, optional/mismatched `item_name`, full item depletion, insufficient quantity / missing item returning HTTP 400 `ResourceError`.
  - Tested canonical condition endpoints: `GET /api/conditions/`, `GET /api/conditions/definitions`, `GET /api/conditions/treatments`, `GET /api/conditions/{condition_id}/treatments`, and `POST /api/conditions/treat`.
  - Verified former duplicate routes (`/api/character/conditions`, `/api/character/treatments`, `/api/character/conditions/{id}/treatments`, `/api/character/conditions/{id}/treat`) return 404.
  - Existing condition test suite `test_conditions.py` passes 41/41.
  - Full test suite `pytest tests/ -q` passes **297 passed**, 275 warnings.
  - `ruff check` reports **0 errors** across entire codebase (all 13 pre-existing errors resolved); `ruff format --check` confirms all 63 files cleanly formatted.
  - Development DB hash remains `6f75dfd7201f6fd370b6ab241832bc15cb0bf672dfda7fe77a4940343e369c2f`.
  - Findings CB-05 and CB-19 are closed.

### STAGE 6 — Global Exception Handling

- **Status:** COMPLETED / VERIFIED.
- **Tasks:**
  - [x] Standardize the error response envelope with top-level `error`, `message`, `details` and backward-compatible `detail` (AGENTS.md §11, CB-04, CB-17).
  - [x] Register global handlers in `app/main.py` via `app.core.errors` for `GameError` (and domain subclasses: `NotFoundError` -> 404, `ValidationError`/`ResourceError`/`ConditionError` -> 400, `ConflictError`/`GameStateError` -> 409, base -> 500), `StarletteHTTPException`, `RequestValidationError` (422), and unexpected `Exception` (500).
  - [x] Remove duplicated per-endpoint `try...except` boilerplate across all API routers (`character.py`, `world.py`, `time.py`, `activities.py`, `conditions.py`, `inventory.py`).
  - [x] Verify database transaction rollback on unhandled domain errors in `get_session()` context manager.
  - [x] Add targeted integration tests in `backend/tests/test_stage6_exception_handling.py` (11 passed).
- **Dependencies:** Stage 0B; recommended after Stage 2 to avoid reworking the
  same endpoint code twice.
- **Acceptance:** consistent error format and status codes across the API;
  request failures roll back the request transaction and return the standard
  envelope.
- **Verification record:**
  - Added `backend/tests/test_stage6_exception_handling.py` with 11 targeted tests (11/11 passed).
  - Verified standard envelope format: top-level `error`, `message`, `details` matching `AGENTS.md` and frontend `ApiError` interface, along with `detail` dict compatibility for existing tests.
  - Verified status code mapping: `NotFoundError` -> 404, `ValidationError` -> 400, `ConflictError` -> 409, `GameStateError` -> 409, generic `GameError` -> 500, `RequestValidationError` -> 422, unhandled `Exception` -> 500.
  - Verified atomic transaction rollback on domain errors without local try/except.
  - Full test suite `pytest tests/ -q` passes **308 passed**, 286 warnings in 165.24s.
  - `ruff check` reports **0 errors** across entire codebase; `ruff format --check` confirms all 65 files cleanly formatted.
  - Development DB hash remains `6f75dfd7201f6fd370b6ab241832bc15cb0bf672dfda7fe77a4940343e369c2f`.
  - Finding CB-17 is closed and backend error envelope for CB-04 is resolved.

### STAGE 7 — Application Startup and World Seeding

- **Status:** COMPLETED / VERIFIED.
- **Tasks:**
  - [x] Make a fresh installation playable (CB-01).
  - [x] Run world seeding safely at startup inside one explicit composition-root transaction.
  - [x] Keep seeding idempotent (`is_world_fully_seeded` check avoids unnecessary writes).
  - [x] Do not call `recreate_db()` at startup.
  - [x] Do not damage or unnecessarily rewrite an existing database.
- **Dependencies:** Stages 0B, 1, 2.
- **Acceptance:** fresh DB can create a character immediately; repeated startup does not duplicate seed data; an existing database remains intact except for missing seed rows or explicitly approved seed-data reconciliation.
- **Verification record:**
  - Implemented `is_world_fully_seeded(session: AsyncSession) -> bool` and `seed_world_if_needed(session: AsyncSession) -> dict` in `app/services/world/seed.py`.
  - Wired `seed_world_at_startup()` into FastAPI application `lifespan(app)` in `app/main.py` using `async with get_session() as session:` composition-root transaction.
  - Guarantees idempotency: checks `is_world_fully_seeded(session)` before seeding. Fully populated databases undergo zero write transactions or file modifications.
  - Fresh installs now immediately create tables and seed kingdom, regions, locations, races, backgrounds, and enemies, making fresh installations playable immediately without manual setup (CB-01).
  - Added 6 targeted integration tests in `backend/tests/test_stage7_startup_seeding.py` verifying fresh DB startup seeding, immediate playable character creation without manual seeding, repeated startup idempotency, partial seed recovery, and regression check that `recreate_db()` is never called.
  - Full test suite passes **314 passed**, 292 warnings in 136.85s.
  - `ruff check` reports **0 errors** across entire codebase (66 files); `ruff format --check` confirms all 66 files cleanly formatted.
  - Development DB hash remains `6f75dfd7201f6fd370b6ab241832bc15cb0bf672dfda7fe77a4940343e369c2f`.
  - Finding CB-01 is closed.

### STAGE 8 — Frontend Foundation

- **Status:** COMPLETED / VERIFIED.
- **Tasks:**
  - [x] Make the API base URL consistent (CB-03, DI-03).
  - [x] Parse backend error responses correctly without producing `undefined` messages (CB-04).
  - [x] Replace CSS classes that are not defined in project styles with pure plain CSS (CB-02).
  - [x] Add loading and error states with Global ErrorBoundary and useApiError hook (PR-09).
  - [x] Resolve ESM `__dirname` in `vite.config.ts` using `fileURLToPath` and `node:url` (PR-03).
  - [x] Add a frontend smoke test and Jest configuration without new dependencies (PR-04).
- **Dependencies:** Stage 6 (error envelope), Stage 7 (playable data).
- **Acceptance:** UI renders correctly, reports meaningful errors, and passes a smoke test.
- **Verification record:**
  - Aligned API base URL and proxy port to `http://localhost:8000` in `frontend/.env`, `frontend/.env.example`, and `frontend/vite.config.ts` (CB-03, DI-03).
  - Resolved ESM `__dirname` in `frontend/vite.config.ts` using standard `fileURLToPath(new URL('./src', import.meta.url))` (PR-03).
  - Aligned `ApiClient` in `frontend/src/api/client.ts` and `frontend/src/types/api.ts`: introduced typed `ApiClientError` parsing Stage 6 top-level `error`, `message`, and `details` with safe fallbacks to `detail` string/object; eliminates all `undefined` error messages (CB-04).
  - Replaced all inert Tailwind classes in `frontend/src/App.tsx` with pure plain CSS semantic classes defined in `frontend/src/styles/main.css` (CB-02).
  - Added `ErrorBoundary` component in `frontend/src/components/ErrorBoundary.tsx` and wrapped `App` in `frontend/src/main.tsx` (PR-09).
  - Added `useApiError` custom hook in `frontend/src/hooks/useApiError.ts` (PR-09).
  - Configured Jest in `frontend/jest.config.cjs` and `frontend/jest.transformer.cjs` supporting ESM/Vite `import.meta.env` and jsdom without adding new dependencies (PR-04).
  - Added 9 unit/smoke tests in `frontend/src/__tests__/smoke.test.tsx` verifying API client, Stage 6 error envelope parsing, detail string parsing, HTTP error fallback, ErrorBoundary crash fallback, useApiError hook, and App rendering under health success and failure (9/9 passed in 1.367s).
  - `npm run lint` clean (0 errors, 0 warnings); `npm run build` clean (Vite bundle generated in 1.15s).
  - Findings CB-02, CB-03, CB-04, PR-03, PR-04, DI-03, and PR-09 are closed.

### STAGE 9 — Documentation and Infrastructure

- **Status:** COMPLETED / VERIFIED.
- **Tasks:**
  - [x] Update README (endpoints, ports, setup accuracy, architecture notes) (DI-01, DI-02).
  - [x] Decide and document logging strategy (`app.core.logging.py` with `JSONFormatter`, DI-06, PR-08).
  - [x] Decide and document migration strategy (configured async Alembic environment, PR-07, IF-08).
  - [x] Resolve project configuration inconsistencies (pinned `package.json` exact versions, DI-05, PR-05; SQLite pool settings documented, DI-04).
  - [x] Add shared constants files (`backend/app/core/constants.py` and `frontend/src/constants.ts`, IF-09).
  - [x] Resolve TD-01 (Ruff check: 0 errors across 69 files) and TD-02 (Ruff format: 69 files formatted) as quality gates.
  - `.gitignore` was already created in Stage 0B.
- **Dependencies:** Stages 1–8 (to reflect actual behavior).
- **Acceptance:** documentation matches behavior; no undocumented dependencies; lint/format debt is closed.
- **Verification record:**
  - Rewrote and updated `README.md` with complete documentation for all 7 API route families, setup guides, development commands, architecture notes, and environment variables (DI-01, DI-02).
  - Documented SQLite single-file concurrency behavior with `aiosqlite` NullPool/file-locking in `README.md` and `database.py`, clarifying that QueuePool parameters (`pool_size`, `max_overflow`) are not applicable to file-based SQLite (DI-04).
  - Pinned exact versions without caret (`^`) ranges in `frontend/package.json` matching installed packages (DI-05, PR-05).
  - Initialized and configured Alembic with async template in `backend/alembic.ini` and `backend/alembic/env.py` pointing to `Base.metadata` and `settings.database_url` (PR-07, IF-08).
  - Implemented structured logging in `backend/app/core/logging.py` (`JSONFormatter`, `setup_logging`) using Python standard library to respect dependency restrictions while satisfying structured logging requirements (DI-06, PR-08).
  - Created shared constants in `backend/app/core/constants.py` and `frontend/src/constants.ts` (IF-09).
  - Verified `ruff check` (0 errors across 69 files) and `ruff format --check` (69 files clean) (TD-01, TD-02).
  - Full backend test suite passes (314 passed); frontend tests pass (9 passed); development DB hash remains `6f75dfd7201f6fd370b6ab241832bc15cb0bf672dfda7fe77a4940343e369c2f`.
  - Findings DI-01, DI-02, DI-04, DI-05, DI-06, PR-05, PR-07, PR-08, TD-01, TD-02, IF-08, and IF-09 are closed.

### STAGE 10 — Incomplete Gameplay Features

- **Status:** IN PROGRESS (Increment 1 COMPLETED / VERIFIED; Increments 2–8 pending).
- **Increments:**
  1. Event system. (COMPLETED / VERIFIED)
  2. NPC interaction. (PLANNED)
  3. Combat system. (PLANNED)
  4. Death and legacy. (PLANNED)
  5. Reincarnation / next generation. (PLANNED)
  6. Session summary. (PLANNED)
  7. Frontend gameplay screens. (PLANNED)
  8. Integration and acceptance testing. (PLANNED)
- **Dependencies:** Stages 1–9. Must not be mixed with fundamental bug fixes.
- **Planning rule:** each increment requires its own plan, branch, approval, and
  acceptance checklist. Do not bundle multiple increments in one change.
- **Acceptance:** each increment is playable end-to-end for its scope and is
  verified against the relevant `SPEC.md` acceptance criteria.
- **Increment 1 (Event System) Verification Record:**
  - Implemented 24 predefined event definitions in `backend/app/services/events/definitions.py` covering all 10 `EventCategory` types (encounter, discovery, danger, opportunity, social, moral_choice, mystery, crisis, fortune, misfortune) per SPEC §6.4 & §13.
  - Defined Pydantic schemas in `backend/app/schemas/events.py` (`EventChoiceOptionSchema`, `EventDisplaySchema`, `EventResolutionResponse`, `StatCheckResultSchema`, `ActiveEventResponse`, `TriggerEventRequest`, `ResolveEventChoiceRequest`).
  - Created authoritative domain service in `backend/app/services/events/service.py` (`get_eligible_events`, `trigger_event`, `get_active_event`, `resolve_event_choice`, `get_all_event_definitions`) with deterministic stat checks (1d20 + modifier >= DC) using `SeededRNG`, state delta application (health, stamina, money, skills, attributes, conditions), death handling with `DeathCause.EVENT_CONSEQUENCES`, and active event lifecycle persistence.
  - Implemented FastAPI router in `backend/app/api/events.py` with 4 endpoints:
    - `GET /api/events/definitions` — list all predefined events
    - `GET /api/events/active` — inspect current active event for session
    - `POST /api/events/trigger` — trigger random eligible or forced event
    - `POST /api/events/choose` — resolve choice, roll stat checks, apply consequences
  - Registered `/api/events` router in `backend/app/main.py`.
  - Added 14 comprehensive tests in `backend/tests/test_stage10_event_system.py` verifying catalog integrity, category coverage, active event lifecycle, consequence application, stat check determinism, deceased character rejection, and death cause recording (14/14 passed).
  - Development DB hash remained `6f75dfd7201f6fd370b6ab241832bc15cb0bf672dfda7fe77a4940343e369c2f`.
  - Finding `IF-01` is closed.

---

## E. Current Position

- **Stage 0A — Backup and hash verification:** COMPLETED.
- **Stage 0B — Test database isolation:** COMPLETED.
- **Stage 0C — Additional verification:** NOT REQUIRED AS A SEPARATE STAGE.
- **Stage 1 — Deterministic RNG and seed validation:** COMPLETED / VERIFIED.
- **Plan audit and architecture anchor:** COMPLETED / APPROVED (2026-11-11).
- **Stage 2 — Transaction Ownership:** COMPLETED / VERIFIED.
- **Stage 2A — Test isolation gate:** COMPLETED / VERIFIED.
- **Stage 3 — Authoritative Time System:** COMPLETED / VERIFIED.
- **Stage 3A — Time-authority regression tests:** COMPLETED / VERIFIED.
- **Stage 3B — Consolidate time engine:** COMPLETED / VERIFIED.
- **Stage 3C — Activities use authoritative time:** COMPLETED / VERIFIED.
- **Stage 3D — API alignment & error handling:** COMPLETED / VERIFIED.
- **Stage 3E — Verification:** COMPLETED / VERIFIED.
- **Stage 3F — Documentation:** COMPLETED / VERIFIED.
- **Stage 4 — Resource and Condition Mathematics:** COMPLETED / VERIFIED.
- **Stage 5 — Inventory and Treatment Consolidation:** COMPLETED / VERIFIED.
- **Stage 6 — Global Exception Handling:** COMPLETED / VERIFIED.
- **Stage 7 — Application Startup and World Seeding:** COMPLETED / VERIFIED.
- **Stage 8 — Frontend Foundation:** COMPLETED / VERIFIED.
- **Stage 9 — Documentation and Infrastructure:** COMPLETED / VERIFIED.
- **Stage 10 — Incomplete Gameplay Features:** IN PROGRESS. Increment 1 (Event system) COMPLETED / VERIFIED; Increment 2 (NPC interaction) is next.
- **All remediation stages (0 through 9) and Stage 10 Increment 1 are completed and verified.**

---

## F. Known Audit Findings

> These findings are recorded from the prior audit. They were not independently
> re-audited while creating this roadmap. A plan audit on 2026-11-11 confirmed
> the current code structure and updated mappings/statuses where direct evidence
> existed; it did not remediate the findings. `OPEN` means reported and not yet
> remediated. IDs are stable for progress tracking.

### Critical

| ID | Finding | Remediation | Status |
|----|---------|-------------|--------|
| CB-01 | Fresh install cannot play: world is not seeded at startup; character creation needs races/backgrounds/locations. | Stage 7 | CLOSED — Lifespan startup seeds all static world data inside a composition-root transaction if not already seeded; fresh DB is playable immediately |
| CB-02 | Frontend uses undefined Tailwind-style classes not present in project CSS. | Stage 8 | CLOSED — Replaced undefined Tailwind classes in App.tsx with semantic plain CSS in styles/main.css |
| CB-03 | API base URL/port inconsistent (backend 8000 vs frontend config/UI 8001/8000). | Stage 8 | CLOSED — Aligned API base URL and proxy port to 8000 across backend, frontend .env, .env.example, and vite.config.ts |
| CB-04 | Frontend parses the wrong error field, producing `undefined` messages. | Stage 8 / Stage 6 | CLOSED — Backend returns top-level envelope (Stage 6); frontend ApiClient parses error/message/details with safe fallback (Stage 8); no undefined messages |
| CB-05 | `use_item` validates `item_id` but consumes `item_name`. | Stage 5 | CLOSED — use_item validates and consumes by authoritative item_id |
| CB-06 | Tests previously called `recreate_db()` against the development database. | Stage 0B | CLOSED — full suite passed with development DB hash unchanged during tests |
| CB-07 | Two `advance_time` implementations; conditions do not tick when activities cross midnight. | Stage 3 | CLOSED — duplicate removed; all paths use the authoritative engine and tick conditions once per elapsed day |

### High

| ID | Finding | Remediation | Status |
|----|---------|-------------|--------|
| CB-08 | Personality generation uses unseeded `random.choice`. | Stage 1 | CLOSED — seeded RNG implemented |
| CB-09 | Seed data uses invalid skill `stealth`; it is silently dropped. | Stage 1 | CLOSED — Orphan corrected; validation added |
| CB-10 | Interrupted rest subtracts health loss twice. | Stage 4 | CLOSED — Interrupted rest health change matches actual character health delta |
| CB-11 | Duplicate health-bound validators (sync and async). | Stage 4 | CLOSED — Single shared validate_health_bounds implementation |
| CB-17 | No global exception handler; error handling is duplicated per endpoint. | Stage 6 | CLOSED — Global handlers registered; standard error envelope implemented; endpoint boilerplate removed |
| CB-19 | Duplicate condition/treatment routes and divergent `TreatmentRequest` schemas. | Stage 5 | CLOSED — canonical /api/conditions namespace and shared schemas; duplicate routes removed |
| PR-01 | Services commit internally, breaking multi-table transaction boundaries. | Stage 2 | CLOSED — service/API commits removed; caller-owned transactions verified |
| IF-01…IF-05 | Event system, NPC, combat, death/legacy/reincarnation, session summary are absent. | Stage 10 | OPEN |

### Medium

| ID | Finding | Remediation | Status |
|----|---------|-------------|--------|
| CB-12 | `conditions.py` `__main__` block references an unimported `TREATMENTS` symbol. | Stage 4 | CLOSED — Debug block and unimported TREATMENTS symbol removed |
| CB-13 | `severity or base` / `duration or max` ignore valid zero values. | Stage 4 | CLOSED — Severity and duration handle zero overrides; negative values rejected |
| CB-14 | Stamina percentage can exceed 100. | Stage 4 | CLOSED — Stamina, health, and fatigue percentages clamped to [0.0, 100.0] |
| CB-15 | Activity stamina validation ignores effective stamina. | Stage 4 | CLOSED — Available stamina is checked against effective max stamina limit |
| CB-16 | Condition effects are applied after commit. | Stage 4 | CLOSED — Stage 2 removed the service commit; effects now share the activity transaction. Stage 4 still verifies condition math. |
| CB-18 | `current_period` is hardcoded in the time API. | Stage 3 | CLOSED — /api/time/periods returns real period when session_token provided, null otherwise; 404 on invalid session |
| PR-03 | `__dirname` in `vite.config.ts` under ESM. | Stage 8 | CLOSED — Replaced __dirname with fileURLToPath(new URL('./src', import.meta.url)) |
| PR-04 | `npm test` points to Jest without config/setup. | Stage 8 | CLOSED — Configured Jest (jest.config.cjs, transformer) and added frontend smoke test suite (9 passed) |
| PR-07 | No Alembic migrations; schema relies on `create_all`. | Stage 9 | CLOSED — Alembic initialized and configured with async template (alembic.ini, alembic/env.py) |
| PR-08 | No `structlog`/structured logging configuration despite `AGENTS.md` §11. | Stage 9 | CLOSED — Implemented structured logging in app.core.logging with JSONFormatter option |
| PR-12 | `AdvanceTimeResponse` omits fields returned by the service. | Stage 3 | CLOSED — AdvanceTimeResponse includes days_advanced and expired_conditions |
| DI-03 | Frontend `.env` and `.env.example` disagree on API port. | Stage 8/9 | CLOSED — Aligned frontend .env and .env.example to port 8000 |
| — | Dead code in activities services; missing `__all__` exports for condition/inventory routers. | Stages 4/5 | OPEN |

### Low

| ID | Finding | Remediation | Status |
|----|---------|-------------|--------|
| DI-01 | README endpoint list is stale. | Stage 9 | CLOSED — README updated with all 7 API route families, setup instructions, and architecture notes |
| DI-02 | README mentions migrations "when available". | Stage 9 | CLOSED — README clarifies automatic startup schema initialization & optional Alembic async migrations |
| DI-04 | AGENTS §4 pool settings do not match SQLite implementation. | Stage 9 | CLOSED — Documented SQLite connection behavior with aiosqlite (NullPool/file lock) in database.py & README |
| DI-05 | `package.json` uses caret ranges, violating exact pinning. | Stage 9 | CLOSED — Exact pinned all dependencies in frontend/package.json without caret ranges |
| DI-06 | `structlog` is required by AGENTS but absent from requirements. | Stage 9 | CLOSED — Implemented structured logging in app.core.logging adhering to standard library constraints in AGENTS.md §7 |
| PR-02 | Empty `session_token` silently creates a new session. | Stage 10 | OPEN |
| PR-05 | Caret dependency ranges allow drift. | Stage 9 | CLOSED — Exact pinned all dependencies in frontend/package.json without caret ranges |
| PR-09 | No frontend error boundary / API error hook. | Stage 8 | CLOSED — Implemented ErrorBoundary component, useApiError hook, and visual error states |
| PR-10 | RNG seed fallback (`rng_seed or session_id`) semantics are ambiguous. | Stage 4 | CLOSED — Explicit rng_seed if rng_seed is not None else ... fallback allows 0 as valid seed |
| PR-11 | Legacy tests may share state / depend on ordering. | Stage 2 gate / ongoing | CLOSED — `test_activities_api.py`, `test_skill_progression.py`, `test_time_api.py`, and `test_character_progression.py` now pass standalone; full suite passes. |
| — | `CharacterCreateRequest` has no session token path for generations. | Stage 10 | OPEN |
| — | Missing tests for inventory/treatment/determinism/frontend. | Ongoing | OPEN |
| TD-01 | `ruff check app tests` reports 22 pre-existing errors outside Stage 1 scope (unused imports, f-strings, undefined `TREATMENTS`, unused variable). | Stage 9 quality gate | CLOSED — Ruff check passes 0 errors across entire repository (69 files) |
| TD-02 | `ruff format --check app tests` reports 5 pre-existing files that would be reformatted. | Stage 9 quality gate | CLOSED — Ruff format check passes with all 69 files cleanly formatted |
| TD-03 | `test_time_api.py` and `test_character_progression.py` fail when run standalone because their `_setup_db()` helpers are never invoked; they pass only due to test ordering/leftover DB state. | Stage 2 gate | CLOSED — both files now use function-scoped autouse DB fixtures and pass standalone. |

### Incomplete Features

| ID | Feature | Remediation | Status |
|----|---------|-------------|--------|
| IF-01 | Event system (20–30 events, choices, consequences). | Stage 10 | CLOSED — 24 predefined events, deterministic stat checks, consequence application, and active event lifecycle verified |
| IF-02 | NPC profiles, dialogue, relationships, memory flags. | Stage 10 | OPEN |
| IF-03 | Combat system (3–5 enemy types, turn-based actions). | Stage 10 | OPEN |
| IF-04 | Death, life record, legacy, reincarnation. | Stage 10 | OPEN |
| IF-05 | Session summary and session history. | Stage 10 | OPEN |
| IF-06 | Frontend screens: Main Menu, Character Creation, Gameplay, Profile, Combat, Death/Reincarnation, Session Summary. | Stages 8/10 | OPEN |
| IF-07 | Missing test coverage (inventory, treatment, determinism, frontend). | Ongoing | OPEN |
| IF-08 | Alembic migrations. | Stage 9 | CLOSED — Alembic async migrations initialized and configured |
| IF-09 | `app/core/constants.py` for shared constants. | Stage 9 | CLOSED — Created backend/app/core/constants.py and frontend/src/constants.ts |

**Caveat:** presence in this list does **not** mean a finding was independently
confirmed during this roadmap update. It means it was reported by the audit and
has not been closed by a verified remediation stage.

---

## G. Testing and Verification Status

- **Test files available:** 12 test files from the last audit, plus the Stage 0B
  canary (`backend/tests/test_db_isolation_canary.py`), the Stage 1 test file
  (`backend/tests/test_stage1_rng_and_skills.py`), the Stage 2 transaction test
  file (`backend/tests/test_transaction_ownership.py`), the Stage 3
  time-authority test file (`backend/tests/test_stage3_time_authority.py`), the
  Stage 4 resource-math test file (`backend/tests/test_stage4_resource_math.py`),
  the Stage 5 inventory-consolidation test file (`backend/tests/test_stage5_inventory_consolidation.py`),
  the Stage 6 exception-handling test file (`backend/tests/test_stage6_exception_handling.py`),
  the Stage 7 startup-seeding test file (`backend/tests/test_stage7_startup_seeding.py`), and
  the Stage 10 event system test file (`backend/tests/test_stage10_event_system.py`) —
  21 files total under `backend/tests/`.
- **Canary isolation:** 4 passed (test DB selection, `recreate_db()` on test DB,
  `recreate_db()` rejection of dev DB, dev DB unchanged after test writes).
- **Ruff check:** 0 errors across entire repository (all 73 files clean).
- **Ruff format check:** 73 files already cleanly formatted.
- **Full test suite:** `pytest tests/ -q` — **328 passed**, 306 warnings in 126.96s
  (2026-11-19, after Stage 10 Increment 1 completion).
- **Frontend test suite:** `npm test --prefix frontend` — **9 passed**
  (2026-11-19, after Stage 9 completion).
- **Frontend build & lint:** `npm run build` succeeds (Vite bundle); `npm run lint` 0 errors.
- **Stage 2A isolation verification:** `test_time_api.py` — 7 passed standalone;
  `test_character_progression.py` — 14 passed standalone; both together — 21
  passed. TD-03 and PR-11 are closed.
- **Legacy test suite:** all previously order-dependent test files now initialize
  their own database state and pass standalone. The full suite also passes.
- **Development database:** repaired during Stage 1. Current SHA-256
  `6f75dfd7201f6fd370b6ab241832bc15cb0bf672dfda7fe77a4940343e369c2f`
  (290,816 bytes). Pre-repair hash was
  `5c746a7a0611b3af21bae1398a68546b2dcb0868b381bc7d42bef06881903824`;
  backup is stored at
  `/tmp/opencode/isekai-db-backups/isekai.db.bak.20261111T083905207573128Z`.
  Hash remained unchanged during Stage 2A, Stage 2, Stage 3, Stage 4, Stage 5,
  Stage 6, Stage 7, Stage 8, and Stage 9 final completion verification.
- **Test database artifact:** `backend/test_isekai.db` was created by the canary
  run and is gitignored; the session fixture removes stale test DB files on the
  next run.
- **Known warning:** `SAWarning` about an unresolvable foreign-key dependency
  between `character_legacies` and `characters` during `DROP` still exists and is
  not yet handled. It does not fail the canary, but should be considered when
  addressing schema/migration work.

---

## H. Development Rules

1. One stage has one clear scope.
2. Do not mix bug fixing with large feature additions.
3. Do not change `SPEC.md` or `AGENTS.md` without approval.
4. Do not add dependencies without approval.
5. Do not delete existing tests just to make the suite pass.
6. Do not delete or recreate the development database.
7. Do not run tests that could destructively affect the development database.
8. Schema changes and migrations require separate consideration and approval.
9. Every stage must have acceptance criteria and verification.
10. Update `ROADMAP.md` after a stage is completed and its results are reported.

---

## Maintenance Rules

`ROADMAP.md` is a living document. After each completed stage:

- Update the stage status.
- Record what was actually changed.
- Record tests run and their results.
- Record remaining findings.
- Update the current position.
- Do not change the status of other work without evidence.

Do not update this file based only on plans or assumptions.

---

## Document History

| Date | Change |
|------|--------|
| 2026-11-09 | Initial `ROADMAP.md` created from `SPEC.md`, `AGENTS.md`, project structure, test inventory, and prior progress reports. |
| 2026-11-11 | Stage 1 completed: deterministic RNG, seed validation, Orphan skill correction, PR-11 repair for two test files, full-suite verification, and development database repair. |
| 2026-11-11 | Plan audit and architecture anchor approved. Added Stage 2 task list and gate; corrected Stage 3–10 dependencies, finding mappings, and quality-gate ownership. No implementation changes. |
| 2026-11-11 | Stage 2A completed: added per-test DB fixtures to `test_time_api.py` and `test_character_progression.py`; both pass standalone and in the full suite. TD-03 and PR-11 closed. |
| 2026-11-11 | Stage 2 completed: removed service/API commits, kept caller-owned transactions, added transaction regression tests, verified 267 passing tests and unchanged dev DB hash. PR-01 and CB-16 closed. |
| 2026-11-11 | Stage 1 and Stage 2 confirmation rerun: dedicated tests 16 passed; full suite 267 passed; development DB hash unchanged. |
| 2026-11-11 | Stage 3A completed: added `test_stage3_time_authority.py`; 6 expected failures and 2 passing baselines confirm the duplicate engine and missing condition ticks. No implementation changes. |
| 2026-11-11 | Stage 3B/3C completed: removed duplicate `advance_time`, routed travel/activities through `game.time.advance_time`, removed world export, and closed CB-07. Targeted tests 90 passed; full suite 275 passed; dev DB hash unchanged. |
| 2026-11-17 | Stage 3 completed: aligned API responses (PR-12 `days_advanced` & `expired_conditions`, CB-18 optional `session_token` with `null` default and 404 error mapping), added test coverage in `test_time_api.py` (9/9 passed), verified full suite (277 passed), and preserved dev DB hash. Closed CB-18 and PR-12. |
| 2026-11-17 | Stage 4 completed: fixed interrupted rest health change delta (CB-10), consolidated single async `validate_health_bounds` (CB-11), removed debug block with undefined `TREATMENTS` (CB-12), handled 0-overrides and negative validation for condition severity/duration (CB-13), clamped resource percentages to [0.0, 100.0] (CB-14), checked available stamina against effective max stamina (CB-15), clarified deterministic RNG seed fallback allowing seed 0 (PR-10), and verified condition effects persist in caller transaction (CB-16). Targeted tests 9/9 passed, full suite 286 passed, dev DB hash unchanged. |
| 2026-11-17 | Stage 5 completed: resolved item identity mismatch in use_item to consume strictly by item_id (CB-05), consolidated condition and treatment routes under canonical /api/conditions namespace, moved condition treatment query to GET /api/conditions/{id}/treatments, removed duplicate routes from /api/character, unified TreatmentRequest/Response schemas in schemas/conditions.py, fixed local variable shadowing bug in inventory service (F823), resolved all 13 remaining project Ruff errors (0 errors across codebase), added 11 integration tests in test_stage5_inventory_consolidation.py (11/11 passed), verified full test suite (297 passed), and preserved dev DB hash. Closed CB-05 and CB-19. |
| 2026-11-17 | Stage 6 completed: implemented global exception handling architecture in app.core.errors and app/main.py, established consistent error envelope (error, message, details, and backward-compatible detail mapping), mapped GameError subclasses and HTTP errors to standard status codes (400, 404, 409, 422, 500), removed duplicated try/except error handling across all API routers, verified transaction rollback on domain errors, added 11 integration tests in test_stage6_exception_handling.py (11/11 passed), verified full test suite (308 passed), confirmed 0 Ruff errors, and preserved dev DB hash. Closed CB-17 and backend error envelope for CB-04. |
| 2026-11-18 | Stage 7 completed: implemented idempotent startup world seeding in app/services/world/seed.py (is_world_fully_seeded, seed_world_if_needed) and wired seed_world_at_startup into lifespan in app/main.py using explicit composition-root transaction; ensures fresh installs are immediately playable without manual setup (CB-01); added 6 targeted integration tests in test_stage7_startup_seeding.py (6/6 passed); verified full test suite (314 passed); 0 Ruff errors; preserved dev DB hash. Closed CB-01. |
| 2026-11-18 | Stage 8 completed: aligned API base URL and proxy port to 8000 across frontend .env, .env.example, and vite.config.ts (CB-03, DI-03); resolved ESM __dirname in vite.config.ts (PR-03); aligned ApiClient and types to Stage 6 error envelope eliminating undefined error messages (CB-04); replaced undefined Tailwind classes in App.tsx with semantic plain CSS in styles/main.css (CB-02); added ErrorBoundary component and useApiError hook (PR-09); configured Jest with transformer and added 9 frontend smoke/foundation tests in smoke.test.tsx (9/9 passed, PR-04); frontend lint and build pass cleanly. Closed CB-02, CB-03, CB-04, PR-03, PR-04, DI-03, PR-09. |
| 2026-11-19 | Stage 9 completed: updated README.md with comprehensive endpoint list, ports, and architecture notes (DI-01, DI-02); documented SQLite aiosqlite connection pool behavior (DI-04); pinned exact dependencies in frontend/package.json without caret ranges (DI-05, PR-05); initialized and configured Alembic async migration environment (PR-07, IF-08); implemented structured logging in app.core.logging with JSONFormatter option (DI-06, PR-08); created shared constants in backend/app/core/constants.py and frontend/src/constants.ts (IF-09); verified ruff check (0 errors across 69 files) and ruff format (69 files clean) (TD-01, TD-02); preserved dev DB hash; verified backend (314 passed) and frontend (9 passed) test suites. Closed DI-01, DI-02, DI-04, DI-05, DI-06, PR-05, PR-07, PR-08, TD-01, TD-02, IF-08, IF-09. |
| 2026-11-19 | Stage 10 Increment 1 completed: implemented event system with 24 predefined event definitions spanning all 10 EventCategory types in app.services.events.definitions (IF-01); established event schemas in app.schemas.events; created authoritative domain service in app.services.events.service with deterministic stat checks, consequence execution (health, stamina, money, skills, attributes, conditions), death handling with DeathCause.EVENT_CONSEQUENCES, and active event lifecycle; registered /api/events API router in app.main; added 14 comprehensive tests in test_stage10_event_system.py (14/14 passed); 0 Ruff errors across 73 files; verified full backend test suite (328 passed); preserved dev DB hash. Closed IF-01. |
