# Isekai: A Life Unwritten
## Project Specification

**Project Type:** Single-player Text-Based RPG  
**Genre:** Anime Isekai, Dark Fantasy, Life Simulation  
**Development Goal:** One-session coding benchmark for FCC  
**Target Gameplay Duration:** 15–30 minutes  
**Version:** 0.1.0

---

# 1. Project Overview

Isekai: A Life Unwritten is a single-player, text-based RPG set in an original anime-inspired fantasy world.

The player is reincarnated into a fantasy world without being destined to become a hero, chosen one, or world savior.

The player begins as an ordinary individual with a randomly generated identity, race, background, and attributes.

They must navigate life in a dangerous world filled with magic, monsters, political conflicts, social inequality, and unpredictable events.

Every decision can influence the character's life, relationships, abilities, and survival.

Death is not necessarily the end. When a character dies, their soul may be reincarnated into another life, carrying a limited legacy from previous generations.

## Core Philosophy

- The world does not revolve around the player.
- The player is not inherently special.
- Choices must have meaningful consequences.
- Death must matter.
- Ordinary life must be as valid as adventure.
- The world should feel dangerous but believable.
- Every playthrough should have some variation.

---

# 2. Narrative Direction

## 2.1 Story Style

**Anime Isekai Fantasy**

The presentation should resemble Japanese fantasy anime and light-novel-inspired RPGs.

Narrative characteristics:

- Expressive NPC dialogue.
- Distinctive character personalities.
- Fantasy races and magical abilities.
- Adventurer guilds, kingdoms, dungeons, and ancient ruins.
- Character-driven encounters.
- Dramatic events and unexpected consequences.
- A mixture of everyday life and dangerous adventures.

Avoid Western medieval fantasy clichés as the primary design inspiration.

The world should feel like an original Japanese anime-style isekai setting.

## 2.2 Tone

**Dark Fantasy**

The world is beautiful but unforgiving.

Themes may include:

- Death and mortality.
- Poverty and social inequality.
- Racial discrimination.
- Political corruption.
- Religious manipulation.
- War and territorial conflict.
- Dangerous magic.
- Human greed and betrayal.
- The consequences of personal decisions.

Dark fantasy should emerge through world events and gameplay consequences, not excessive violence or meaningless cruelty.

Include occasional peaceful moments, humor, friendship, and hope to create narrative contrast.

---

# 3. World Setting

Create one original fantasy kingdom.

The world must be small enough for a one-session benchmark but sufficiently detailed to support multiple character paths.

## 3.1 Kingdom

**Kingdom Name:** Eldoria

Eldoria is an old kingdom experiencing political instability, economic inequality, and increasing monster activity.

Magic is widely known but not equally accessible to everyone.

The kingdom has three primary regions:

### A. Royal Capital — Aetheria

- Political and economic center.
- Royal palace and noble districts.
- Adventurer guild headquarters.
- Magic academy.
- Commercial markets.
- Significant social inequality.

### B. Frontier Region — Valdren

- Dangerous settlements near monster territories.
- Adventurer outposts.
- Mining and hunting communities.
- Abandoned ruins.
- High mortality among inexperienced adventurers.

### C. Sacred Forest — Elarion

- Ancient forest inhabited by elves and magical creatures.
- Hidden villages.
- Ancient shrines.
- Rare magical resources.
- Dangerous unexplored territories.

## 3.2 Locations

Create approximately 5–8 explorable locations across these regions.

Each location should have:
- A unique identity.
- Relevant NPCs.
- Available activities.
- Possible random encounters.
- Location-specific events.

Do not implement a massive open world.

---

# 4. Races

Implement six playable races.

| Race | Characteristics |
|---|---|
| Human | Balanced attributes and adaptable |
| Elf | High intelligence and magical affinity |
| Beastkin | High agility and physical senses |
| Dwarf | High vitality and craftsmanship |
| Dragonkin | High strength and natural resistance |
| Demonkin | High magical potential but socially discriminated against |

Each race should have:
- A short lore description.
- Attribute modifiers.
- One racial trait.
- Relevant social implications.

Race selection must not lock the player into a specific profession or story path.

---

# 5. Character System

## 5.1 Character Creation

The player begins a new life by generating a character.

Character properties:

- Name.
- Race.
- Gender presentation.
- Age.
- Background.
- Personality trait.
- Attributes.
- Starting location.
- Initial resources.

Allow the player to choose a name.

Generate the remaining properties randomly, with an option to reroll before starting.

## 5.2 Backgrounds

Implement at least five backgrounds:

1. Commoner
2. Merchant Family
3. Orphan
4. Noble Descendant
5. Former Slave

Backgrounds influence:
- Starting resources.
- Initial relationships.
- Available dialogue options.
- Starting skills.
- Social opportunities.

Backgrounds should create different starting conditions, not predetermined storylines.

## 5.3 Attributes

Use five primary attributes:

| Attribute | Function |
|---|---|
| Strength | Physical power and combat |
| Agility | Speed, evasion, and dexterity |
| Intelligence | Knowledge and magic |
| Vitality | Health and endurance |
| Luck | Random outcomes and opportunities |

Use a simple numerical scale.

Attributes must affect gameplay outcomes.

## 5.4 Skills

Skills improve through relevant activities.

Examples:

- Swordsmanship
- Archery
- Magic
- Healing
- Cooking
- Trading
- Crafting
- Survival
- Negotiation

Do not implement a complicated skill tree.

Use simple experience and progression mechanics.

---

# 6. Gameplay System

## 6.1 Core Gameplay Loop

The primary gameplay cycle:

1. Generate a character.
2. Enter the fantasy world.
3. Receive an introductory situation.
4. Explore locations and interact with NPCs.
5. Encounter events and make decisions.
6. Gain or lose resources, health, skills, and relationships.
7. Experience life progression.
8. Eventually reach death or a session ending.
9. Record the character's legacy.
10. Reincarnate into another life.

The game must support at least two consecutive lives within one play session.

## 6.2 Time System

Implement a simplified in-game time system.

- Morning
- Afternoon
- Evening
- Night

Actions consume time.

Some events and NPC availability depend on time.

The game should allow time to advance through activities and event transitions.

## 6.3 Player Activities

Allow the player to perform several activities:

- Explore.
- Work.
- Trade.
- Train.
- Rest.
- Socialize.
- Accept quests.
- Hunt monsters.
- Visit locations.

Activities must have meaningful effects on character state.

## 6.4 Decision System

Events should present contextual choices.

Example:

A merchant offers the player a suspiciously profitable job.

Possible choices:

1. Accept the job.
2. Negotiate payment.
3. Refuse.
4. Investigate the merchant.

Each choice should produce consequences.

Consequences may affect:
- Health.
- Money.
- Inventory.
- Skills.
- Relationships.
- Reputation.
- Time.
- Future event availability.

Avoid choices that only change narrative text without affecting game state.

## 6.5 Random Events

Implement approximately 20–30 predefined events.

Event categories:

- Daily life.
- Social encounters.
- Economic opportunities.
- Monster encounters.
- Combat.
- Travel.
- Accidents.
- Illness.
- Political incidents.
- Rare events.

Use weighted randomness and contextual conditions.

Events should not be entirely random. Character attributes, location, background, time, and previous decisions should influence available events.

---

# 7. NPC System

Implement 10–15 important NPCs.

Each NPC should have:

- Name.
- Race.
- Age.
- Personality.
- Occupation.
- Location.
- Relationship with the player.
- Basic dialogue.
- Memory of important player decisions where applicable.

NPC personality examples:

- Friendly.
- Suspicious.
- Greedy.
- Compassionate.
- Arrogant.
- Manipulative.

Implement a simple relationship scale.

NPC relationships should influence dialogue and selected event outcomes.

NPCs do not need autonomous AI behavior or complex daily simulation.

---

# 8. Combat System

Implement lightweight turn-based combat.

Combat should use:

- Player attributes.
- Skills.
- Enemy attributes.
- Equipment.
- Random variation.
- Health and damage calculations.

Basic actions:

- Attack.
- Defend.
- Use skill.
- Escape.

Create approximately 3–5 enemy types.

Examples:

- Slime.
- Goblin.
- Dire Wolf.
- Skeleton.
- Corrupted Beast.

Combat should be dangerous.

A poorly prepared character may die even during relatively ordinary encounters.

---

# 9. Death and Reincarnation

This is the game's defining mechanic.

## 9.1 Death

A character can die due to:

- Combat.
- Severe injuries.
- Illness.
- Dangerous exploration.
- Event consequences.

Death should not be arbitrarily forced.

The game must record the cause of death.

## 9.2 Soul Record

After death, generate a life record containing:

- Character identity.
- Race.
- Background.
- Age at death.
- Cause of death.
- Important decisions.
- Achievements.
- Relationships.
- Skills.
- Final resources.

## 9.3 Reincarnation

After death, the player can start a new life.

The new character receives:
- A new identity.
- A new background.
- A new starting location.
- New attributes.
- A different initial situation.

A limited legacy may carry over from previous lives.

Examples:
- Fragmented memories.
- Minor skill affinity.
- A recurring dream.
- A small inherited bonus.

Legacy must be limited. Do not make each reincarnation overwhelmingly stronger than the previous one.

Support at least two generations in one session.

---

# 10. Session Ending

The benchmark does not require endless gameplay.

Provide a session summary after the player completes at least two lives or chooses to end the session.

The summary should show:

- Total generations.
- Characters created.
- Total time lived.
- Important decisions.
- Death records.
- Skills developed.
- Legacy passed between lives.

The player should be able to start another session from the beginning.

---

# 11. Technical Architecture

## 11.1 Technology Stack

### Backend
- Python 3.12+
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic

### Frontend
- React
- TypeScript
- Vite
- CSS or a lightweight styling solution

### Testing
- Pytest for backend.
- Basic frontend tests where appropriate.
- Manual browser testing.

## 11.2 Architecture

Use a modular monolith.

Suggested backend modules:

- `character`: character generation and attributes.
- `world`: locations, regions, and world data.
- `game`: session and gameplay state.
- `events`: event selection and consequences.
- `combat`: combat calculations.
- `npc`: NPC profiles and relationships.
- `reincarnation`: death records and legacy.
- `database`: persistence and models.
- `api`: HTTP endpoints.

Keep game rules separate from API handlers.

The frontend should not directly implement authoritative game calculations.

The backend owns game state and validates every action.

## 11.3 Database

Use SQLite.

Persist:
- Game sessions.
- Characters.
- Character attributes.
- Inventory.
- Skills.
- NPC relationships.
- Life records.
- Reincarnation legacy.
- Current gameplay state.

A game session must survive a browser refresh.

## 11.4 Randomness

Use a controlled random number generator.

Support a session seed so gameplay can be reproduced during testing.

Avoid uncontrolled random behavior that makes bugs difficult to reproduce.

## 11.5 API

Create REST endpoints for:

- Creating a game session.
- Generating a character.
- Starting a life.
- Retrieving current game state.
- Performing activities.
- Selecting event choices.
- Starting combat.
- Performing combat actions.
- Processing death.
- Reincarnating.
- Retrieving life history.
- Ending a session.

Use appropriate request and response schemas.

---

# 12. User Interface

Create an immersive anime-inspired dark fantasy interface.

## Visual Direction

- Dark fantasy atmosphere.
- Deep charcoal backgrounds.
- Muted gold accents.
- Dark crimson for danger and critical states.
- Elegant serif display typography paired with readable UI typography.
- Subtle fantasy ornamentation.
- Clear visual hierarchy.

Avoid excessive decorative elements that interfere with readability.

## Main Screens

### A. Main Menu
- New Game.
- Continue Game.
- Session History.

### B. Character Creation
- Name input.
- Character details.
- Random generation.
- Reroll.
- Start Life.

### C. Main Gameplay
- Character status panel.
- Current location.
- Time and day.
- Narrative/event panel.
- Available choices.
- Activity actions.
- NPC interaction.

### D. Character Profile
- Attributes.
- Skills.
- Inventory.
- Relationships.
- Background.

### E. Combat
- Player status.
- Enemy status.
- Combat log.
- Available actions.

### F. Death and Reincarnation
- Death narrative.
- Life record.
- Legacy information.
- Reincarnation action.

### G. Session Summary
- Life history.
- Important events.
- Generational legacy.

The interface must be responsive and usable on desktop and mobile.

---

# 13. Benchmark Scope

The following limits are intentional.

| Component | Target |
|---|---:|
| Kingdoms | 1 |
| Regions | 3 |
| Locations | 5–8 |
| Playable races | 6 |
| Backgrounds | 5 |
| Important NPCs | 10–15 |
| Event definitions | 20–30 |
| Enemy types | 3–5 |
| Playable generations | At least 2 |
| Gameplay duration | 15–30 minutes |

## Explicitly Out of Scope

Do not implement:

- Multiplayer.
- Persistent online world.
- Real-time simulation.
- Autonomous NPC AI.
- LLM-powered Game Master.
- Procedural infinite world generation.
- Complex economy simulation.
- Large-scale kingdom politics simulation.
- Advanced equipment crafting.
- Complicated skill trees.
- Voice acting.
- Animation-heavy combat.
- Authentication or user registration.
- Payment systems.
- Deployment infrastructure.

Do not expand scope without explicit approval.

---

# 14. Acceptance Criteria

The project is considered successful when:

1. The application starts locally using documented commands.
2. The player can create a new game session.
3. Character generation works correctly.
4. The player can perform multiple activities.
5. Event choices produce actual state changes.
6. Attributes influence gameplay outcomes.
7. NPC interactions work.
8. Combat can be completed or result in death.
9. Death generates a complete life record.
10. Reincarnation creates a new playable character.
11. Previous life legacy affects the next generation in a limited way.
12. At least two lives can be played in one session.
13. Session state persists after browser refresh.
14. The session summary displays previous generations.
15. No critical runtime errors prevent gameplay.

---

# 15. Development Rules

- Read the project specification before implementation.
- Build the application in working increments.
- Prioritize a complete gameplay loop over excessive content.
- Do not create placeholder buttons that do nothing.
- Do not fake backend functionality in the frontend.
- Keep game rules deterministic where possible.
- Validate all player actions on the backend.
- Include meaningful error handling.
- Add tests for important game mechanics.
- Do not silently remove or simplify required features.
- Document setup and execution instructions.
- Do not introduce unnecessary dependencies or infrastructure.

**Final Objective:**

Deliver a functional, playable, single-session anime isekai dark fantasy RPG where the player can experience an ordinary life, make consequential decisions, die, reincarnate, and witness the legacy of previous lives.

The benchmark is about completing a coherent game experience, not maximizing feature count.
