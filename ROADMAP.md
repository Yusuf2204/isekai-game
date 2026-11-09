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
| Backend foundation | PARTIAL | FastAPI app, async SQLAlchemy engine/session, models, schemas, config, routers. Missing global exception handler, startup seeding, migrations. |
| Core gameplay systems | PARTIAL | Character creation, progression, resources, conditions, time, world locations, activities, inventory/treatment. Events, NPC, combat, death/legacy, reincarnation, session summary not implemented. |
| Backend reliability and remediation | IN PROGRESS | Stage 0 (database safety) completed. Stage 1 (deterministic RNG and seed validation) is next. |
| Frontend | PARTIAL | Vite/React scaffold and a health screen. Main Menu, Character Creation, Gameplay, Profile, Combat, Death/Reincarnation, Session Summary screens not implemented. Known CSS/URL/error-parsing issues. |
| Gameplay completeness | PARTIAL | No complete end-to-end gameplay loop yet (no events, combat, death, reincarnation, or session summary). |
| Integration and acceptance testing | NOT STARTED | Full backend suite not run. Frontend tests not runnable as configured. Acceptance criteria in `SPEC.md` §14 not yet demonstrated. |

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
| `NOT VERIFIED` | Implemented or reported, but not independently confirmed. |

`IMPLEMENTED` does **not** imply `TESTED` or `VERIFIED`. A phase may hold several
statuses for different subtasks.

---

## C. Completed Development Phases

> The phases below are recorded as implemented from project history. Unless a
> phase explicitly says `TESTED`/`VERIFIED`, its behavior has **not** been
> independently verified during this roadmap update. The full test suite has not
> been run.

| Phase | Description | Status |
|-------|-------------|--------|
| **PART 0 — Specification and agent guidelines** | `SPEC.md` (product spec, scope, acceptance criteria) and `AGENTS.md` (architecture, conventions, dependencies, testing rules) exist. | IMPLEMENTED |
| **PART 1 — Project foundation** | Backend FastAPI app, health endpoint, config, async DB engine/session, React + Vite scaffold, initial health UI. | IMPLEMENTED / PARTIAL (frontend is health-only) / NOT VERIFIED |
| **PART 2 — Database and world foundation** | SQLAlchemy models for sessions, characters, attributes, skills, inventory, NPC relationships, life records, legacy, gameplay state, kingdom/regions/locations/races/backgrounds/enemies. Seed data for Eldoria, 3 regions, 7 locations, 6 races, 5 backgrounds, enemies. | IMPLEMENTED / PARTIAL (startup seeding not wired; one invalid seed skill) / NOT VERIFIED |
| **PART 3A — Character creation foundation** | Character creation service, schemas, endpoint, random identity generation, racial modifiers, backgrounds, personality, starting skills/location, session token. | IMPLEMENTED / PARTIAL (non-deterministic personality; invalid `stealth` skill) / NOT VERIFIED |
| **PART 3B — Character initialization** | Initial money, health/resources, inventory, starting skills, game session and gameplay state initialization. | IMPLEMENTED / NOT VERIFIED |
| **PART 3C — World, time, and basic activities** | Location/world API, time API and periods, activities (explore, work, rest, train, socialize, trade), travel, activity log. | IMPLEMENTED / PARTIAL (duplicate `advance_time`; condition ticking inconsistency) / NOT VERIFIED |
| **PART 3D — Character progression** | Attribute points, attribute experience, skill experience/levels, unified progression status. | IMPLEMENTED / NOT VERIFIED |
| **PART 3E.1 — Health and resources** | Health/stamina/fatigue status, health changes, stamina/fatigue penalties and resource endpoints. | IMPLEMENTED / PARTIAL (duplicate health validator; stamina percentage bounds) / NOT VERIFIED |
| **PART 3E.2 — Stamina, fatigue, and conditions** | Condition model (severity, duration), condition effects, fatigue, stamina penalties, treatment scaffolding. | IMPLEMENTED / PARTIAL (zero-value handling, effective stamina, debug block bug) / NOT VERIFIED |
| **PART 3E.3-R2 — Money, inventory, and treatment atomicity** | Money changes, inventory add/remove/use, treatments, transaction-oriented revisions. | IMPLEMENTED / PARTIAL (item identity mismatch; duplicate condition/treatment routes; service-level commits) / NOT VERIFIED |

---

## D. Audit and Remediation Roadmap

> **No stage below is approved for implementation by default.** Stages 1–10 are
> `PLANNED` unless explicitly stated otherwise. Each stage requires separate
> approval before code changes, and must not be bundled with large feature work.

### STAGE 0 — Database Safety

| Subtask | Status | Notes |
|---------|--------|-------|
| **0A — Backup and hash verification** | COMPLETED | Development DB backed up outside the active DB directory; SHA-256 verified identical. |
| **0B — Test database isolation** | COMPLETED | `backend/conftest.py`, `backend/pytest.ini`, path-based `recreate_db()` guard, `.gitignore`, and a canary test. Canary: 4 passed. Full suite not run. |
| **0C — Additional verification** | NOT REQUIRED AS A SEPARATE STAGE | Canary verification was performed during 0B. Full-suite verification remains future work. |

- **Stage 0A record:** source `backend/isekai.db`, 290,816 bytes, SHA-256
  `5c746a7a0611b3af21bae1398a68546b2dcb0868b381bc7d42bef06881903824`.
  Backup: `/tmp/opencode/isekai-db-backups/isekai.db.bak.20261109T162523466960865Z.2324868`.
- **Stage 0B record:** tests use `backend/test_isekai.db`; `recreate_db()` refuses
  any path other than the resolved `backend/test_isekai.db`; development DB hash
  unchanged after the canary run.

### STAGE 1 — Deterministic RNG and Seed Validation

- **Status:** PLANNED — NEXT, NOT STARTED.
- **Tasks:**
  - Use the seeded RNG (`app.core.rng`) for personality generation.
  - Validate seed skill names against the skill enum.
  - Handle invalid seed skills without silent failure.
- **Dependencies:** Stage 0B.
- **Acceptance:** no uncontrolled `random` use in game logic; same seed yields
  deterministic results; invalid seed data fails loudly or is corrected.

### STAGE 2 — Transaction Ownership

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Remove commits from service layer; services flush only.
  - Manage transaction boundaries at the request/unit-of-work layer.
  - Audit every caller before changing commit behavior.
- **Dependencies:** Stage 0B.
- **Acceptance:** multi-table operations remain atomic; no partial writes on
  failure; no service-level commit.

### STAGE 3 — Authoritative Time System

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Consolidate `advance_time` into one authoritative implementation.
  - Make activities, travel, and time API use the same time source.
  - Prevent double condition ticking.
  - Align time response schemas with actual returned fields.
- **Dependencies:** Stage 2.
- **Acceptance:** one time-advancement path; conditions tick exactly once per
  elapsed day across all paths.

### STAGE 4 — Resource and Condition Mathematics

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Correct health change calculations (including interrupted rest).
  - Make effective stamina consistent across validation and display.
  - Clamp stamina percentage to valid bounds.
  - Validate `severity` and `duration` correctly, including zero values.
  - Consolidate duplicate health-bound validators.
  - Fix condition-effect ordering relative to commit.
  - Remove or repair related dead code and debug blocks.
- **Dependencies:** Stages 2, 3.
- **Acceptance:** reported resource changes match persisted state; no double
  penalties; validators have a single implementation.

### STAGE 5 — Inventory and Treatment Consolidation

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Make item identity consistent (id vs name) for validation and consumption.
  - Consolidate duplicate condition/treatment routes.
  - Consolidate `TreatmentRequest` schemas.
  - Add relevant integration tests.
- **Dependencies:** Stages 2, 4.
- **Acceptance:** one contract per inventory/treatment operation; no item
  identity mismatch; integration tests exist.

### STAGE 6 — Global Exception Handling

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Standardize the error response envelope.
  - Handle `GameError` and unexpected exceptions globally.
  - Remove duplicated per-endpoint error handling where appropriate.
- **Dependencies:** Stage 0B (can proceed independently of Stages 2–5, with care).
- **Acceptance:** consistent error format and status codes across the API.

### STAGE 7 — Application Startup and World Seeding

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Make a fresh installation playable.
  - Run world seeding safely at startup.
  - Keep seeding idempotent.
  - Do not damage an existing database.
- **Dependencies:** Stages 0B, 1.
- **Acceptance:** fresh DB can create a character immediately; repeated startup
  does not duplicate seed data.

### STAGE 8 — Frontend Foundation

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Make the API base URL consistent.
  - Parse backend error responses correctly.
  - Replace CSS classes that are not defined in project styles.
  - Add loading and error states.
  - Add a frontend smoke test consistent with approved dependencies/config.
- **Dependencies:** Stage 6 (error envelope), Stage 7 (playable data).
- **Notes:** dependency and configuration changes require separate approval.
- **Acceptance:** UI renders correctly, reports meaningful errors, and passes a
  smoke test.

### STAGE 9 — Documentation and Infrastructure

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Update README (endpoints, ports, setup accuracy).
  - Decide and document logging strategy.
  - Decide and document migration strategy.
  - Resolve project configuration inconsistencies.
  - `.gitignore` was already created in Stage 0B.
- **Dependencies:** Stages 1–8 (to reflect actual behavior).
- **Notes:** dependency additions (e.g., logging, migrations) require separate
  approval.
- **Acceptance:** documentation matches behavior; no undocumented dependencies.

### STAGE 10 — Incomplete Gameplay Features

- **Status:** PLANNED — NOT STARTED. Each item below is a separate increment and
  requires its own approval.
- **Increments:**
  1. Event system.
  2. NPC interaction.
  3. Combat system.
  4. Death and legacy.
  5. Reincarnation / next generation.
  6. Session summary.
  7. Frontend gameplay screens.
  8. Integration and acceptance testing.
- **Dependencies:** Stages 1–9. Must not be mixed with fundamental bug fixes.
- **Acceptance:** each increment is playable end-to-end for its scope and is
  verified against the relevant `SPEC.md` acceptance criteria.

---

## E. Current Position

- **Stage 0A — Backup and hash verification:** COMPLETED.
- **Stage 0B — Test database isolation:** COMPLETED.
- **Stage 0C — Additional verification:** NOT REQUIRED AS A SEPARATE STAGE.
- **Stage 1 — Deterministic RNG and seed validation:** NEXT — PLANNED,
  NOT STARTED.
- **No remediation implementation is currently in progress.**
- All subsequent stages require explicit approval before implementation.

---

## F. Known Audit Findings

> These findings are recorded from the prior audit. They were not independently
> re-audited while creating this roadmap. `OPEN` means reported and not yet
> remediated. IDs are stable for progress tracking.

### Critical

| ID | Finding | Remediation | Status |
|----|---------|-------------|--------|
| CB-01 | Fresh install cannot play: world is not seeded at startup; character creation needs races/backgrounds/locations. | Stage 7 | OPEN |
| CB-02 | Frontend uses undefined Tailwind-style classes not present in project CSS. | Stage 8 | OPEN |
| CB-03 | API base URL/port inconsistent (backend 8000 vs frontend config/UI 8001/8000). | Stage 8 | OPEN |
| CB-04 | Frontend parses the wrong error field, producing `undefined` messages. | Stage 8 | OPEN |
| CB-05 | `use_item` validates `item_id` but consumes `item_name`. | Stage 5 | OPEN |
| CB-06 | Tests previously called `recreate_db()` against the development database. | Stage 0B | MITIGATED — full-suite verification pending |
| CB-07 | Two `advance_time` implementations; conditions do not tick when activities cross midnight. | Stage 3 | OPEN |

### High

| ID | Finding | Remediation | Status |
|----|---------|-------------|--------|
| CB-08 | Personality generation uses unseeded `random.choice`. | Stage 1 | OPEN |
| CB-09 | Seed data uses invalid skill `stealth`; it is silently dropped. | Stage 1 | OPEN |
| CB-10 | Interrupted rest subtracts health loss twice. | Stage 4 | OPEN |
| CB-11 | Duplicate health-bound validators (sync and async). | Stage 4 | OPEN |
| CB-17 | No global exception handler; error handling is duplicated per endpoint. | Stage 6 | OPEN |
| CB-19 | Duplicate condition/treatment routes and divergent `TreatmentRequest` schemas. | Stage 5 | OPEN |
| PR-01 | Services commit internally, breaking multi-table transaction boundaries. | Stage 2 | OPEN |
| IF-01…IF-05 | Event system, NPC, combat, death/legacy/reincarnation, session summary are absent. | Stage 10 | OPEN |

### Medium

| ID | Finding | Remediation | Status |
|----|---------|-------------|--------|
| CB-12 | `conditions.py` `__main__` block references an unimported `TREATMENTS` symbol. | Stage 4 | OPEN |
| CB-13 | `severity or base` / `duration or max` ignore valid zero values. | Stage 4 | OPEN |
| CB-14 | Stamina percentage can exceed 100. | Stage 4 | OPEN |
| CB-15 | Activity stamina validation ignores effective stamina. | Stage 4 | OPEN |
| CB-16 | Condition effects are applied after commit. | Stage 4 | OPEN |
| CB-18 | `current_period` is hardcoded in the time API. | Stage 3 | OPEN |
| PR-03 | `__dirname` in `vite.config.ts` under ESM. | Stage 8 | OPEN |
| PR-04 | `npm test` points to Jest without config/setup. | Stage 8 | OPEN |
| PR-07 | No Alembic migrations; schema relies on `create_all`. | Stage 9 | OPEN |
| PR-08 | No `structlog`/structured logging configuration despite `AGENTS.md` §11. | Stage 9 | OPEN |
| PR-12 | `AdvanceTimeResponse` omits fields returned by the service. | Stage 3 | OPEN |
| DI-03 | Frontend `.env` and `.env.example` disagree on API port. | Stage 8/9 | OPEN |
| — | Dead code in activities services; missing `__all__` exports for condition/inventory routers. | Stages 4/5 | OPEN |

### Low

| ID | Finding | Remediation | Status |
|----|---------|-------------|--------|
| DI-01 | README endpoint list is stale. | Stage 9 | OPEN |
| DI-02 | README mentions migrations "when available". | Stage 9 | OPEN |
| DI-04 | AGENTS §4 pool settings do not match SQLite implementation. | Stage 9 | OPEN |
| DI-05 | `package.json` uses caret ranges, violating exact pinning. | Stage 9 | OPEN |
| DI-06 | `structlog` is required by AGENTS but absent from requirements. | Stage 9 | OPEN |
| PR-02 | Empty `session_token` silently creates a new session. | Stage 10 | OPEN |
| PR-05 | Caret dependency ranges allow drift. | Stage 9 | OPEN |
| PR-09 | No frontend error boundary / API error hook. | Stage 8 | OPEN |
| PR-10 | RNG seed fallback (`rng_seed or session_id`) semantics are ambiguous. | Stage 1 | OPEN |
| PR-11 | Legacy tests may share state / depend on ordering. | Stage 0B / ongoing | OPEN |
| — | `CharacterCreateRequest` has no session token path for generations. | Stage 10 | OPEN |
| — | Missing tests for inventory/treatment/determinism/frontend. | Ongoing | OPEN |

### Incomplete Features

| ID | Feature | Remediation | Status |
|----|---------|-------------|--------|
| IF-01 | Event system (20–30 events, choices, consequences). | Stage 10 | OPEN |
| IF-02 | NPC profiles, dialogue, relationships, memory flags. | Stage 10 | OPEN |
| IF-03 | Combat system (3–5 enemy types, turn-based actions). | Stage 10 | OPEN |
| IF-04 | Death, life record, legacy, reincarnation. | Stage 10 | OPEN |
| IF-05 | Session summary and session history. | Stage 10 | OPEN |
| IF-06 | Frontend screens: Main Menu, Character Creation, Gameplay, Profile, Combat, Death/Reincarnation, Session Summary. | Stages 8/10 | OPEN |
| IF-07 | Missing test coverage (inventory, treatment, determinism, frontend). | Ongoing | OPEN |
| IF-08 | Alembic migrations. | Stage 9 | OPEN |
| IF-09 | `app/core/constants.py` for shared constants. | Stage 9 | OPEN |

**Caveat:** presence in this list does **not** mean a finding was independently
confirmed during this roadmap update. It means it was reported by the audit and
has not been closed by a verified remediation stage.

---

## G. Testing and Verification Status

- **Test files available:** 12 test files from the last audit, plus 1 canary test
  file added in Stage 0B (`backend/tests/test_db_isolation_canary.py`) — 13 files
  total under `backend/tests/`.
- **Canary isolation:** 4 passed (test DB selection, `recreate_db()` on test DB,
  `recreate_db()` rejection of dev DB, dev DB unchanged after test writes).
- **Ruff check:** passed on the last verification.
- **Ruff format check:** passed on the last verification.
- **Full test suite:** **NOT RUN**.
- **Legacy test suite:** must not be run until every test is confirmed to use the
  test database. Stage 0B provides isolation, but full-suite verification is
  still pending.
- **Development database:** unchanged since Stage 0A, SHA-256
  `5c746a7a0611b3af21bae1398a68546b2dcb0868b381bc7d42bef06881903824`
  (290,816 bytes).
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
