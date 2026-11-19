/** Integration tests for Stage 10 Increment 7: Frontend Gameplay Screens.
 *
 * Verifies rendering, contracts, and interactions for:
 * - MainMenuScreen
 * - CharacterCreationScreen
 * - CombatScreen
 * - DeathReincarnationScreen
 * - SessionSummaryScreen
 * - SessionHistoryScreen
 */

import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import { GameProvider, useGame } from '../context/GameContext';
import { MainMenuScreen } from '../screens/MainMenuScreen';
import { CharacterCreationScreen } from '../screens/CharacterCreationScreen';
import { CombatScreen } from '../screens/CombatScreen';
import { DeathReincarnationScreen } from '../screens/DeathReincarnationScreen';
import { SessionSummaryScreen } from '../screens/SessionSummaryScreen';
import { SessionHistoryScreen } from '../screens/SessionHistoryScreen';

describe('Stage 10 Increment 7: Frontend Screens Integration', () => {
  const originalFetch = globalThis.fetch;
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    localStorage.clear();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    container.remove();
  });

  it('renders MainMenuScreen with title, action buttons, and backend health status', async () => {
    globalThis.fetch = jest.fn((url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes('/api/health')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          statusText: 'OK',
          json: () =>
            Promise.resolve({
              status: 'healthy',
              version: '0.1.0',
              service: 'isekai-backend',
            }),
        } as Response);
      }
      return Promise.reject(new Error(`Unhandled URL: ${urlStr}`));
    });

    const root = createRoot(container);

    await act(async () => {
      root.render(
        <GameProvider>
          <MainMenuScreen />
        </GameProvider>
      );
    });

    expect(container.textContent).toContain('Isekai: A Life Unwritten');
    expect(container.textContent).toContain('Begin New Life');
    expect(container.textContent).toContain('Continue (No Saved Game)');
    expect(container.textContent).toContain('Chronicles of Past Lives');

    await act(async () => {
      root.unmount();
    });
  });

  it('renders CharacterCreationScreen with races, backgrounds, and identity controls', async () => {
    globalThis.fetch = jest.fn((url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes('/api/character/races')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          statusText: 'OK',
          json: () =>
            Promise.resolve([
              {
                name: 'human',
                display_name: 'Human',
                description: 'Versatile and adaptable.',
                lore: 'Humans arrived centuries ago.',
                strength_modifier: 0,
                agility_modifier: 0,
                intelligence_modifier: 0,
                vitality_modifier: 0,
                luck_modifier: 0,
                racial_trait_name: 'Adaptable Spirit',
                racial_trait_description: '+1 to any attribute.',
              },
              {
                name: 'elf',
                display_name: 'Elf',
                description: 'Ancient forest kin.',
                lore: 'Guardians of Elarion.',
                strength_modifier: 0,
                agility_modifier: 2,
                intelligence_modifier: 1,
                vitality_modifier: -1,
                luck_modifier: 0,
                racial_trait_name: 'Keen Senses',
                racial_trait_description: 'Heightened precision.',
              },
            ]),
        } as Response);
      }
      if (urlStr.includes('/api/character/backgrounds')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          statusText: 'OK',
          json: () =>
            Promise.resolve([
              {
                name: 'commoner',
                display_name: 'Commoner',
                description: 'Humble folk.',
                starting_money: 50,
                starting_skills: { farming: 1 },
              },
            ]),
        } as Response);
      }
      return Promise.reject(new Error(`Unhandled URL: ${urlStr}`));
    });

    const root = createRoot(container);

    await act(async () => {
      root.render(
        <GameProvider>
          <CharacterCreationScreen />
        </GameProvider>
      );
    });

    expect(container.textContent).toContain('Genesis of a New Life');
    expect(container.textContent).toContain('Mortal Name');
    expect(container.textContent).toContain('Gender Presentation');
    expect(container.textContent).toContain('Lineage & Race');
    expect(container.textContent).toContain('Background & Social Origin');
    expect(container.textContent).toContain('Awaken in Eldoria');

    await act(async () => {
      root.unmount();
    });
  });

  it('renders CombatScreen with player/enemy stats and 5 turn actions', async () => {
    // Custom wrapper that seeds active combat state
    const CombatTestHarness = () => {
      const { dispatch } = useGame();
      React.useEffect(() => {
        dispatch({
          type: 'SET_COMBAT_STATE',
          combat: {
            status: 'active',
            turn: 1,
            player_initiative: 15,
            enemy_initiative: 12,
            player_goes_first: true,
            enemy: {
              id: 'slime_01',
              name: 'Forest Slime',
              enemy_type: 'slime',
              level: 1,
              current_health: 20,
              max_health: 20,
              attack_power: 5,
              defense: 2,
              agility: 6,
              description: 'A gelatinous creature oozing acidic slime.',
            },
            player: {
              current_health: 50,
              max_health: 50,
              current_stamina: 80,
              max_stamina: 100,
              level: 1,
            },
            combat_log: ['Combat initiated with Forest Slime! Player rolls initiative 15 vs 12.'],
          },
        });
      }, [dispatch]);

      return <CombatScreen />;
    };

    const root = createRoot(container);

    await act(async () => {
      root.render(
        <GameProvider>
          <CombatTestHarness />
        </GameProvider>
      );
    });

    expect(container.textContent).toContain('Encounter: Forest Slime');
    expect(container.textContent).toContain('Turn-Based Combat');
    expect(container.textContent).toContain('Choose Turn Action');
    expect(container.textContent).toContain('Attack (-10 STA)');
    expect(container.textContent).toContain('Defend (+5 STA, -50% DMG)');
    expect(container.textContent).toContain('Strike Skill (-15 STA)');
    expect(container.textContent).toContain('Use Potion');
    expect(container.textContent).toContain('Flee Battle');

    await act(async () => {
      root.unmount();
    });
  });

  it('renders DeathReincarnationScreen with obituary, legacy, and reincarnation button', async () => {
    const DeathTestHarness = () => {
      const { dispatch } = useGame();
      React.useEffect(() => {
        dispatch({
          type: 'SET_DEATH_AND_LEGACY',
          lifeRecord: {
            id: 1,
            character_id: 10,
            character_name: 'Alden the Brave',
            generation: 1,
            race: 'Human',
            background: 'Commoner',
            age_at_death: 24,
            days_lived: 32,
            death_cause: 'combat',
            obituary: 'Slain in battle by a dire wolf in the Whispering Forest.',
            final_attributes: { strength: 12, agility: 11 },
            final_skills: { swordsmanship: 3 },
            final_money: 120,
            achievements: ['First Blood', 'Monster Hunter'],
          },
          legacy: {
            id: 1,
            character_id: 10,
            bonus_attribute: 'strength',
            bonus_attribute_value: 1,
            skill_affinity: 'swordsmanship',
            skill_affinity_bonus: 1,
            money_bonus: 25,
            personality_memory: 'You remember the cold fangs of the wolf and the thrill of the blade.',
            unlocked_at_generation: 1,
          },
        });
      }, [dispatch]);

      return <DeathReincarnationScreen />;
    };

    const root = createRoot(container);

    await act(async () => {
      root.render(
        <GameProvider>
          <DeathTestHarness />
        </GameProvider>
      );
    });

    expect(container.textContent).toContain('THE VESSEL PERISHES');
    expect(container.textContent).toContain('Alden the Brave');
    expect(container.textContent).toContain('Cause: combat');
    expect(container.textContent).toContain('Slain in battle by a dire wolf');
    expect(container.textContent).toContain('Ancestral Legacy Left Behind');
    expect(container.textContent).toContain('+1 STRENGTH for Next Generation');
    expect(container.textContent).toContain('Reincarnate into Generation 2');

    await act(async () => {
      root.unmount();
    });
  });

  it('renders SessionSummaryScreen with multi-generation lineage and statistics', async () => {
    const SummaryTestHarness = () => {
      const { dispatch } = useGame();
      React.useEffect(() => {
        dispatch({
          type: 'SET_SESSION_SUMMARY',
          summary: {
            session_id: 1,
            session_token: 'test_token_123',
            is_active: false,
            current_generation: 2,
            total_characters: 2,
            total_days_lived: 58,
            total_achievements: 3,
            characters: [
              {
                id: 1,
                generation: 1,
                name: 'Alden',
                race_name: 'Human',
                background_name: 'Commoner',
                is_alive: false,
                age: 25,
                days_lived: 30,
                money: 150,
                death_cause: 'combat',
                obituary: 'Fell bravely against highway brigands.',
                achievements: ['First Blood'],
              },
              {
                id: 2,
                generation: 2,
                name: 'Lyra',
                race_name: 'Elf',
                background_name: 'Merchant Family',
                is_alive: false,
                age: 26,
                days_lived: 28,
                money: 420,
                death_cause: 'retired',
                obituary: 'Retired in prosperity to Luminaris.',
                achievements: ['Wealthy Patron', 'Master Negotiator'],
              },
            ],
          },
        });
      }, [dispatch]);

      return <SessionSummaryScreen />;
    };

    const root = createRoot(container);

    await act(async () => {
      root.render(
        <GameProvider>
          <SummaryTestHarness />
        </GameProvider>
      );
    });

    expect(container.textContent).toContain('CHRONICLES OF THE TRANSMIGRATED SOUL');
    expect(container.textContent).toContain('TOTAL GENERATIONS');
    expect(container.textContent).toContain('CONCLUDED');
    expect(container.textContent).toContain('Gen 1: Alden');
    expect(container.textContent).toContain('Gen 2: Lyra');
    expect(container.textContent).toContain('Return to Main Menu');
    expect(container.textContent).toContain('Begin a Brand New Journey');

    await act(async () => {
      root.unmount();
    });
  });

  it('renders SessionHistoryScreen with archived sessions list', async () => {
    globalThis.fetch = jest.fn((url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes('/api/session/history')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          statusText: 'OK',
          json: () =>
            Promise.resolve({
              total: 1,
              sessions: [
                {
                  id: 1,
                  session_token: 'hist_token_abc',
                  is_active: false,
                  current_generation: 2,
                  created_at: '2026-11-19T00:00:00Z',
                  total_characters: 2,
                  character_names: ['Alden', 'Lyra'],
                },
              ],
            }),
        } as Response);
      }
      return Promise.reject(new Error(`Unhandled URL: ${urlStr}`));
    });

    const root = createRoot(container);

    await act(async () => {
      root.render(
        <GameProvider>
          <SessionHistoryScreen />
        </GameProvider>
      );
    });

    expect(container.textContent).toContain('Archived Chronicles');
    expect(container.textContent).toContain('Session #1');
    expect(container.textContent).toContain('Concluded');
    expect(container.textContent).toContain('Alden → Lyra');

    await act(async () => {
      root.unmount();
    });
  });
});
