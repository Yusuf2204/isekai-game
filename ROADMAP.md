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
| Backend reliability and remediation | IN PROGRESS | Stages 0, 1, 2, and 3 completed and verified. Stage 4 next. |
| Frontend | PARTIAL | Vite/React scaffold and a health screen. Main Menu, Character Creation, Gameplay, Profile, Combat, Death/Reincarnation, Session Summary screens not implemented. Known CSS/URL/error-parsing issues. |
| Gameplay completeness | PARTIAL | No complete end-to-end gameplay loop yet (no events, combat, death, reincarnation, or session summary). |
| Integration and acceptance testing | PARTIAL | Full backend suite passes (277 passed). Frontend tests not runnable as configured. Acceptance criteria in `SPEC.md` §14 not yet demonstrated. |

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

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Correct health change calculations (including interrupted rest).
  - Make effective stamina consistent across validation and display.
  - Clamp stamina percentage to valid bounds.
  - Validate `severity` and `duration` correctly, including zero values.
  - Consolidate duplicate health-bound validators.
  - Verify condition effects remain in the request transaction after Stage 2;
    do not reintroduce commits inside activity services.
  - Clarify activity RNG seed fallback semantics (`rng_seed or session_id`) as
    part of activity correctness (PR-10).
  - Remove or repair related dead code and debug blocks.
- **Dependencies:** Stages 2, 3.
- **Acceptance:** reported resource changes match persisted state; no double
  penalties; validators have a single implementation; condition effects persist
  in the same transaction as the activity that caused them.

### STAGE 5 — Inventory and Treatment Consolidation

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Choose and document one canonical route namespace for condition/treatment
    operations before coding; remove the duplicate route family.
  - Make item identity consistent (id vs name) for validation and consumption.
  - Consolidate `TreatmentRequest` schemas into one shared schema.
  - Add relevant integration tests.
- **Dependencies:** Stages 2, 4.
- **Acceptance:** one contract per inventory/treatment operation; no item
  identity mismatch; duplicate routes and schemas are removed; integration tests
  exist.

### STAGE 6 — Global Exception Handling

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Standardize the error response envelope.
  - Register global handlers for `GameError` and unexpected exceptions in
    `app/main.py`.
  - Remove duplicated per-endpoint error handling where appropriate.
- **Dependencies:** Stage 0B; recommended after Stage 2 to avoid reworking the
  same endpoint code twice.
- **Acceptance:** consistent error format and status codes across the API;
  request failures roll back the request transaction and return the standard
  envelope.

### STAGE 7 — Application Startup and World Seeding

- **Status:** PLANNED — NOT STARTED.
- **Tasks:**
  - Make a fresh installation playable.
  - Run world seeding safely at startup inside one explicit composition-root
    transaction.
  - Keep seeding idempotent.
  - Do not call `recreate_db()` at startup.
  - Do not damage or unnecessarily rewrite an existing database.
- **Dependencies:** Stages 0B, 1, 2.
- **Acceptance:** fresh DB can create a character immediately; repeated startup
  does not duplicate seed data; an existing database remains intact except for
  missing seed rows or explicitly approved seed-data reconciliation.

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
  - Resolve TD-01 (Ruff check) and TD-02 (Ruff format) as quality gates.
  - `.gitignore` was already created in Stage 0B.
- **Dependencies:** Stages 1–8 (to reflect actual behavior).
- **Notes:** dependency additions (e.g., logging, migrations) require separate
  approval. TD-01/TD-02 must either be fixed or explicitly documented as
  accepted exceptions.
- **Acceptance:** documentation matches behavior; no undocumented dependencies;
  lint/format debt is closed or explicitly waived.

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
- **Planning rule:** each increment requires its own plan, branch, approval, and
  acceptance checklist. Do not bundle multiple increments in one change.
- **Acceptance:** each increment is playable end-to-end for its scope and is
  verified against the relevant `SPEC.md` acceptance criteria.

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
- **Stage 4 — Resource and Condition Mathematics:** Next up (PLANNED).
- **No further remediation implementation is currently in progress.**

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
| CB-01 | Fresh install cannot play: world is not seeded at startup; character creation needs races/backgrounds/locations. | Stage 7 | OPEN |
| CB-02 | Frontend uses undefined Tailwind-style classes not present in project CSS. | Stage 8 | OPEN |
| CB-03 | API base URL/port inconsistent (backend 8000 vs frontend config/UI 8001/8000). | Stage 8 | OPEN |
| CB-04 | Frontend parses the wrong error field, producing `undefined` messages. | Stage 8 | OPEN |
| CB-05 | `use_item` validates `item_id` but consumes `item_name`. | Stage 5 | OPEN |
| CB-06 | Tests previously called `recreate_db()` against the development database. | Stage 0B | CLOSED — full suite passed with development DB hash unchanged during tests |
| CB-07 | Two `advance_time` implementations; conditions do not tick when activities cross midnight. | Stage 3 | CLOSED — duplicate removed; all paths use the authoritative engine and tick conditions once per elapsed day |

### High

| ID | Finding | Remediation | Status |
|----|---------|-------------|--------|
| CB-08 | Personality generation uses unseeded `random.choice`. | Stage 1 | CLOSED — seeded RNG implemented |
| CB-09 | Seed data uses invalid skill `stealth`; it is silently dropped. | Stage 1 | CLOSED — Orphan corrected; validation added |
| CB-10 | Interrupted rest subtracts health loss twice. | Stage 4 | OPEN |
| CB-11 | Duplicate health-bound validators (sync and async). | Stage 4 | OPEN |
| CB-17 | No global exception handler; error handling is duplicated per endpoint. | Stage 6 | OPEN |
| CB-19 | Duplicate condition/treatment routes and divergent `TreatmentRequest` schemas. | Stage 5 | OPEN |
| PR-01 | Services commit internally, breaking multi-table transaction boundaries. | Stage 2 | CLOSED — service/API commits removed; caller-owned transactions verified |
| IF-01…IF-05 | Event system, NPC, combat, death/legacy/reincarnation, session summary are absent. | Stage 10 | OPEN |

### Medium

| ID | Finding | Remediation | Status |
|----|---------|-------------|--------|
| CB-12 | `conditions.py` `__main__` block references an unimported `TREATMENTS` symbol. | Stage 4 | OPEN |
| CB-13 | `severity or base` / `duration or max` ignore valid zero values. | Stage 4 | OPEN |
| CB-14 | Stamina percentage can exceed 100. | Stage 4 | OPEN |
| CB-15 | Activity stamina validation ignores effective stamina. | Stage 4 | OPEN |
| CB-16 | Condition effects are applied after commit. | Stage 4 | CLOSED — Stage 2 removed the service commit; effects now share the activity transaction. Stage 4 still verifies condition math. |
| CB-18 | `current_period` is hardcoded in the time API. | Stage 3 | CLOSED — /api/time/periods returns real period when session_token provided, null otherwise; 404 on invalid session |
| PR-03 | `__dirname` in `vite.config.ts` under ESM. | Stage 8 | OPEN |
| PR-04 | `npm test` points to Jest without config/setup. | Stage 8 | OPEN |
| PR-07 | No Alembic migrations; schema relies on `create_all`. | Stage 9 | OPEN |
| PR-08 | No `structlog`/structured logging configuration despite `AGENTS.md` §11. | Stage 9 | OPEN |
| PR-12 | `AdvanceTimeResponse` omits fields returned by the service. | Stage 3 | CLOSED — AdvanceTimeResponse includes days_advanced and expired_conditions |
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
| PR-10 | RNG seed fallback (`rng_seed or session_id`) semantics are ambiguous. | Stage 4 | DEFERRED — Stage 1 acceptance met without changing fallback semantics; clarify during activity RNG/resource correctness. |
| PR-11 | Legacy tests may share state / depend on ordering. | Stage 2 gate / ongoing | CLOSED — `test_activities_api.py`, `test_skill_progression.py`, `test_time_api.py`, and `test_character_progression.py` now pass standalone; full suite passes. |
| — | `CharacterCreateRequest` has no session token path for generations. | Stage 10 | OPEN |
| — | Missing tests for inventory/treatment/determinism/frontend. | Ongoing | OPEN |
| TD-01 | `ruff check app tests` reports 22 pre-existing errors outside Stage 1 scope (unused imports, f-strings, undefined `TREATMENTS`, unused variable). | Stage 9 quality gate | OPEN |
| TD-02 | `ruff format --check app tests` reports 5 pre-existing files that would be reformatted. | Stage 9 quality gate | OPEN |
| TD-03 | `test_time_api.py` and `test_character_progression.py` fail when run standalone because their `_setup_db()` helpers are never invoked; they pass only due to test ordering/leftover DB state. | Stage 2 gate | CLOSED — both files now use function-scoped autouse DB fixtures and pass standalone. |

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

- **Test files available:** 12 test files from the last audit, plus the Stage 0B
  canary (`backend/tests/test_db_isolation_canary.py`), the Stage 1 test file
  (`backend/tests/test_stage1_rng_and_skills.py`), the Stage 2 transaction test
  file (`backend/tests/test_transaction_ownership.py`), and the Stage 3
  time-authority test file (`backend/tests/test_stage3_time_authority.py`) —
  16 files total under `backend/tests/`.
- **Canary isolation:** 4 passed (test DB selection, `recreate_db()` on test DB,
  `recreate_db()` rejection of dev DB, dev DB unchanged after test writes).
- **Ruff check:** 22 pre-existing errors remain outside Stages 1/2 scope. The
  Stage 2 and Stage 3 test files pass `ruff check`; 7 of the pre-existing errors
  are in `inventory.py`/`activities.py` and remain assigned to Stage 9 (TD-01).
- **Ruff format check:** 5 pre-existing files would be reformatted, including
  `inventory.py`; these remain assigned to Stage 9 (TD-02). The Stage 2 and
  Stage 3 test files are already formatted.
- **Full test suite:** `pytest tests/ -q` — **277 passed**, 256 warnings
  (2026-11-17, after Stage 3 completion).
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
  Hash remained unchanged during Stage 2A, Stage 2, Stage 3B/3C, and Stage 3
  final completion verification.
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
