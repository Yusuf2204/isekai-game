/** Game Context and Reducer for Authoritative State Management.
 *
 * Adheres strictly to AGENTS.md §1 (React Context + useReducer, no Redux/Zustand)
 * and AGENTS.md §4 (Session state persistence across browser refreshes).
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useReducer,
  useCallback,
  type ReactNode,
} from 'react';
import { apiClient } from '../api/client';
import { ApiClientError } from '../types/api';
import type {
  ActiveEvent,
  ActivityOption,
  Character,
  CharacterCreateRequest,
  CharacterLegacy,
  CombatActionResponse,
  CombatState,
  ConditionItem,
  EventResolutionResponse,
  LifeRecord,
  LocationDetailResponse,
  LocationSummary,
  NPCDetail,
  NPCSummary,
  ReincarnateRequest,
  ReincarnationStatusResponse,
  ResourceStatus,
  SessionSummaryResponse,
  TimeState,
  TreatmentItem,
} from '../types/game';

export type ScreenType =
  | 'main_menu'
  | 'character_creation'
  | 'gameplay'
  | 'combat'
  | 'death'
  | 'session_summary'
  | 'history';

export type GameplayTab = 'activities' | 'world' | 'profile' | 'npcs' | 'conditions';

export interface GameState {
  sessionToken: string | null;
  currentScreen: ScreenType;
  activeTab: GameplayTab;
  character: Character | null;
  resources: ResourceStatus | null;
  timeState: TimeState | null;
  locations: LocationSummary[];
  currentLocation: LocationDetailResponse | null;
  activities: ActivityOption[];
  activeEvent: ActiveEvent | null;
  lastEventResolution: EventResolutionResponse | null;
  combatState: CombatState | null;
  lifeRecord: LifeRecord | null;
  legacy: CharacterLegacy | null;
  reincarnationStatus: ReincarnationStatusResponse | null;
  sessionSummary: SessionSummaryResponse | null;
  narrativeLogs: string[];
  locationNpcs: NPCSummary[];
  selectedNpc: NPCDetail | null;
  npcDialogue: { npcName: string; line: string } | null;
  conditions: ConditionItem[];
  availableTreatments: { conditionId: number; treatments: TreatmentItem[] } | null;
  loading: boolean;
  error: string | null;
}

type GameAction =
  | { type: 'SET_LOADING'; loading: boolean }
  | { type: 'SET_ERROR'; error: string | null }
  | { type: 'SET_SCREEN'; screen: ScreenType }
  | { type: 'SET_TAB'; tab: GameplayTab }
  | { type: 'SET_SESSION_TOKEN'; token: string | null }
  | { type: 'SET_CHARACTER'; character: Character | null }
  | { type: 'SET_RESOURCES'; resources: ResourceStatus }
  | { type: 'SET_TIME_STATE'; timeState: TimeState }
  | { type: 'SET_LOCATIONS'; locations: LocationSummary[] }
  | { type: 'SET_CURRENT_LOCATION'; location: LocationDetailResponse }
  | { type: 'SET_ACTIVITIES'; activities: ActivityOption[] }
  | { type: 'SET_ACTIVE_EVENT'; event: ActiveEvent | null }
  | { type: 'SET_LAST_EVENT_RESOLUTION'; resolution: EventResolutionResponse | null }
  | { type: 'SET_COMBAT_STATE'; combat: CombatState | null }
  | { type: 'SET_DEATH_AND_LEGACY'; lifeRecord: LifeRecord | null; legacy: CharacterLegacy | null }
  | { type: 'SET_REINCARNATION_STATUS'; status: ReincarnationStatusResponse | null }
  | { type: 'SET_SESSION_SUMMARY'; summary: SessionSummaryResponse | null }
  | { type: 'ADD_NARRATIVE_LOG'; log: string }
  | { type: 'SET_LOCATION_NPCS'; npcs: NPCSummary[] }
  | { type: 'SET_SELECTED_NPC'; npc: NPCDetail | null }
  | { type: 'SET_NPC_DIALOGUE'; dialogue: { npcName: string; line: string } | null }
  | { type: 'SET_CONDITIONS'; conditions: ConditionItem[] }
  | { type: 'SET_AVAILABLE_TREATMENTS'; treatments: { conditionId: number; treatments: TreatmentItem[] } | null }
  | { type: 'RESET_GAME' };

const STORAGE_KEY = 'isekai_session_token';

const initialState: GameState = {
  sessionToken: typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null,
  currentScreen: 'main_menu',
  activeTab: 'activities',
  character: null,
  resources: null,
  timeState: null,
  locations: [],
  currentLocation: null,
  activities: [],
  activeEvent: null,
  lastEventResolution: null,
  combatState: null,
  lifeRecord: null,
  legacy: null,
  reincarnationStatus: null,
  sessionSummary: null,
  narrativeLogs: [],
  locationNpcs: [],
  selectedNpc: null,
  npcDialogue: null,
  conditions: [],
  availableTreatments: null,
  loading: false,
  error: null,
};

function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.loading };
    case 'SET_ERROR':
      return { ...state, error: action.error, loading: false };
    case 'SET_SCREEN':
      return { ...state, currentScreen: action.screen, error: null };
    case 'SET_TAB':
      return { ...state, activeTab: action.tab };
    case 'SET_SESSION_TOKEN':
      if (action.token) {
        localStorage.setItem(STORAGE_KEY, action.token);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
      return { ...state, sessionToken: action.token };
    case 'SET_CHARACTER':
      return { ...state, character: action.character };
    case 'SET_RESOURCES':
      return { ...state, resources: action.resources };
    case 'SET_TIME_STATE':
      return { ...state, timeState: action.timeState };
    case 'SET_LOCATIONS':
      return { ...state, locations: action.locations };
    case 'SET_CURRENT_LOCATION':
      return { ...state, currentLocation: action.location };
    case 'SET_ACTIVITIES':
      return { ...state, activities: action.activities };
    case 'SET_ACTIVE_EVENT':
      return { ...state, activeEvent: action.event };
    case 'SET_LAST_EVENT_RESOLUTION':
      return { ...state, lastEventResolution: action.resolution };
    case 'SET_COMBAT_STATE':
      return { ...state, combatState: action.combat };
    case 'SET_DEATH_AND_LEGACY':
      return { ...state, lifeRecord: action.lifeRecord, legacy: action.legacy };
    case 'SET_REINCARNATION_STATUS':
      return { ...state, reincarnationStatus: action.status };
    case 'SET_SESSION_SUMMARY':
      return { ...state, sessionSummary: action.summary };
    case 'ADD_NARRATIVE_LOG':
      return {
        ...state,
        narrativeLogs: [action.log, ...state.narrativeLogs].slice(0, 50),
      };
    case 'SET_LOCATION_NPCS':
      return { ...state, locationNpcs: action.npcs };
    case 'SET_SELECTED_NPC':
      return { ...state, selectedNpc: action.npc };
    case 'SET_NPC_DIALOGUE':
      return { ...state, npcDialogue: action.dialogue };
    case 'SET_CONDITIONS':
      return { ...state, conditions: action.conditions };
    case 'SET_AVAILABLE_TREATMENTS':
      return { ...state, availableTreatments: action.treatments };
    case 'RESET_GAME':
      localStorage.removeItem(STORAGE_KEY);
      return {
        ...initialState,
        sessionToken: null,
        currentScreen: 'main_menu',
      };
    default:
      return state;
  }
}

interface GameContextType extends GameState {
  dispatch: React.Dispatch<GameAction>;
  goToScreen: (screen: ScreenType) => void;
  setActiveTab: (tab: GameplayTab) => void;
  startNewGame: () => void;
  continueGame: (token?: string) => Promise<boolean>;
  refreshAuthoritativeState: (token?: string) => Promise<void>;
  createCharacter: (req: CharacterCreateRequest) => Promise<void>;
  reincarnateCharacter: (req: ReincarnateRequest) => Promise<void>;
  performExplore: (locationId?: number) => Promise<void>;
  performRest: (restType: 'short' | 'long') => Promise<void>;
  performWork: (workType: string, locationId?: number) => Promise<void>;
  travelToLocation: (destinationId: number) => Promise<void>;
  advanceTime: (periods: number) => Promise<void>;
  allocateAttributePoint: (attributeName: string, points?: number) => Promise<void>;
  useInventoryItem: (itemId: string, quantity?: number) => Promise<void>;
  treatCondition: (conditionId: number, treatmentId: string) => Promise<void>;
  inspectConditionTreatments: (conditionId: number) => Promise<void>;
  triggerRandomEvent: () => Promise<void>;
  resolveEventChoice: (choiceId: string) => Promise<void>;
  startCombatEncounter: (enemyId?: string) => Promise<void>;
  executeCombatAction: (
    action: 'attack' | 'defend' | 'use_skill' | 'use_item' | 'flee',
    itemId?: string
  ) => Promise<CombatActionResponse>;
  interactWithNpc: (npcId: number, topic?: string) => Promise<void>;
  giftNpc: (npcId: number, payload: { gold_amount?: number; item_id?: string; quantity?: number }) => Promise<void>;
  concludeSession: () => Promise<void>;
  resetToMainMenu: () => void;
}

const GameContext = createContext<GameContextType | undefined>(undefined);

export const GameProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(gameReducer, initialState);

  const goToScreen = useCallback((screen: ScreenType) => {
    dispatch({ type: 'SET_SCREEN', screen });
  }, []);

  const setActiveTab = useCallback((tab: GameplayTab) => {
    dispatch({ type: 'SET_TAB', tab });
  }, []);

  const refreshAuthoritativeState = useCallback(
    async (overrideToken?: string) => {
      const token = overrideToken || state.sessionToken;
      if (!token) return;

      try {
        dispatch({ type: 'SET_LOADING', loading: true });

        // 1. Fetch character
        const character = await apiClient.getCurrentCharacter(token);
        dispatch({ type: 'SET_CHARACTER', character });

        // 2. Fetch resources
        if (character.is_alive) {
          const resources = await apiClient.getResources(token);
          dispatch({ type: 'SET_RESOURCES', resources });
        }

        // 3. Fetch time state
        const timeState = await apiClient.getTimeState(token);
        dispatch({ type: 'SET_TIME_STATE', timeState });

        // 4. Fetch locations
        const locationsResp = await apiClient.getLocations();
        dispatch({ type: 'SET_LOCATIONS', locations: locationsResp.locations });

        // 5. Fetch current location
        const locId = character.starting_location_id || locationsResp.locations[0]?.id;
        if (locId) {
          const locDetail = await apiClient.getLocationDetail(locId);
          dispatch({ type: 'SET_CURRENT_LOCATION', location: locDetail });
        }

        // 6. Check active combat
        try {
          const combat = await apiClient.getCombatState(token);
          if (combat && combat.status === 'active') {
            dispatch({ type: 'SET_COMBAT_STATE', combat });
            dispatch({ type: 'SET_SCREEN', screen: 'combat' });
            return;
          }
        } catch {
          dispatch({ type: 'SET_COMBAT_STATE', combat: null });
        }

        // 7. Check if character died
        if (!character.is_alive) {
          try {
            const lifeRecord = await apiClient.getLifeRecord(character.id);
            let legacy: CharacterLegacy | null = null;
            try {
              legacy = await apiClient.getLegacy(character.id);
            } catch {
              // Legacy may not exist yet or was skipped
            }
            dispatch({ type: 'SET_DEATH_AND_LEGACY', lifeRecord, legacy });
            dispatch({ type: 'SET_SCREEN', screen: 'death' });
            return;
          } catch {
            // Death record fetch failed
          }
        }

        // 8. Fetch activities if alive
        if (character.is_alive) {
          const activitiesResp = await apiClient.getAvailableActivities(token);
          dispatch({ type: 'SET_ACTIVITIES', activities: activitiesResp.activities });

          // 9. Fetch active event if any
          try {
            const event = await apiClient.getActiveEvent(token);
            dispatch({ type: 'SET_ACTIVE_EVENT', event });
          } catch {
            dispatch({ type: 'SET_ACTIVE_EVENT', event: null });
          }

          // 10. Fetch conditions
          try {
            const conditionsResp = await apiClient.getConditions(token);
            dispatch({ type: 'SET_CONDITIONS', conditions: conditionsResp.conditions });
          } catch {
            dispatch({ type: 'SET_CONDITIONS', conditions: [] });
          }
        }

        dispatch({ type: 'SET_ERROR', error: null });
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Failed to synchronize game state';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken]
  );

  const continueGame = useCallback(
    async (token?: string): Promise<boolean> => {
      const activeToken = token || state.sessionToken;
      if (!activeToken) return false;

      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        dispatch({ type: 'SET_SESSION_TOKEN', token: activeToken });
        await refreshAuthoritativeState(activeToken);

        // Character check
        const char = await apiClient.getCurrentCharacter(activeToken);
        if (!char.is_alive) {
          dispatch({ type: 'SET_SCREEN', screen: 'death' });
        } else {
          dispatch({ type: 'SET_SCREEN', screen: 'gameplay' });
        }
        return true;
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Unable to continue previous session';
        dispatch({ type: 'SET_ERROR', error: msg });
        return false;
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, refreshAuthoritativeState]
  );

  const startNewGame = useCallback(() => {
    dispatch({ type: 'RESET_GAME' });
    dispatch({ type: 'SET_SCREEN', screen: 'character_creation' });
  }, []);

  const createCharacter = useCallback(
    async (req: CharacterCreateRequest) => {
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.createCharacter(req);
        dispatch({ type: 'SET_SESSION_TOKEN', token: resp.session_token });
        dispatch({ type: 'SET_CHARACTER', character: resp.character });
        dispatch({
          type: 'ADD_NARRATIVE_LOG',
          log: `Awakened into Eldoria as ${resp.character.name}, a ${resp.character.race_name} ${resp.character.background_name}.`,
        });
        await refreshAuthoritativeState(resp.session_token);
        dispatch({ type: 'SET_SCREEN', screen: 'gameplay' });
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Character creation failed';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [refreshAuthoritativeState]
  );

  const reincarnateCharacter = useCallback(
    async (req: ReincarnateRequest) => {
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.reincarnate(req);
        dispatch({ type: 'SET_CHARACTER', character: resp.character });
        dispatch({
          type: 'ADD_NARRATIVE_LOG',
          log: `The soul transmigrates... Reborn into Generation ${resp.character.generation} as ${resp.character.name}!`,
        });
        await refreshAuthoritativeState(req.session_token);
        dispatch({ type: 'SET_SCREEN', screen: 'gameplay' });
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Reincarnation failed';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [refreshAuthoritativeState]
  );

  const performExplore = useCallback(
    async (locationId?: number) => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.explore(state.sessionToken, locationId);
        dispatch({ type: 'ADD_NARRATIVE_LOG', log: resp.narrative });
        dispatch({ type: 'SET_TIME_STATE', timeState: resp.current_time });
        await refreshAuthoritativeState();
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Explore action failed';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, refreshAuthoritativeState]
  );

  const performRest = useCallback(
    async (restType: 'short' | 'long') => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.rest(state.sessionToken, restType);
        dispatch({ type: 'ADD_NARRATIVE_LOG', log: resp.narrative });
        dispatch({ type: 'SET_TIME_STATE', timeState: resp.current_time });
        await refreshAuthoritativeState();
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Rest action failed';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, refreshAuthoritativeState]
  );

  const performWork = useCallback(
    async (workType: string, locationId?: number) => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.work(state.sessionToken, workType, locationId);
        dispatch({ type: 'ADD_NARRATIVE_LOG', log: resp.narrative });
        dispatch({ type: 'SET_TIME_STATE', timeState: resp.current_time });
        await refreshAuthoritativeState();
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Work action failed';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, refreshAuthoritativeState]
  );

  const travelToLocation = useCallback(
    async (destinationId: number) => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.travel(state.sessionToken, destinationId);
        dispatch({
          type: 'ADD_NARRATIVE_LOG',
          log: `Traveled through Eldoria to ${resp.destination.name}. Time elapsed: ${resp.time_elapsed_periods} period(s).`,
        });
        const locDetail = await apiClient.getLocationDetail(destinationId);
        dispatch({ type: 'SET_CURRENT_LOCATION', location: locDetail });
        await refreshAuthoritativeState();
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Travel failed';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, refreshAuthoritativeState]
  );

  const advanceTime = useCallback(
    async (periods: number) => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.advanceTime(state.sessionToken, periods);
        dispatch({ type: 'SET_TIME_STATE', timeState: resp.current_time });
        dispatch({
          type: 'ADD_NARRATIVE_LOG',
          log: `Time flowed forward by ${periods} period(s). It is now ${resp.current_time.current_time_of_day}, Day ${resp.current_time.current_day}.`,
        });
        await refreshAuthoritativeState();
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Advance time failed';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, refreshAuthoritativeState]
  );

  const allocateAttributePoint = useCallback(
    async (attributeName: string, points: number = 1) => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.allocateAttribute(state.sessionToken, {
          attribute_name: attributeName,
          points,
        });
        dispatch({
          type: 'ADD_NARRATIVE_LOG',
          log: `Allocated ${resp.points_allocated} point(s) to ${resp.attribute_name} (${resp.previous_value} -> ${resp.new_value}).`,
        });
        await refreshAuthoritativeState();
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Attribute allocation failed';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, refreshAuthoritativeState]
  );

  const useInventoryItem = useCallback(
    async (itemId: string, quantity: number = 1) => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.useItem(state.sessionToken, itemId, quantity);
        dispatch({
          type: 'ADD_NARRATIVE_LOG',
          log: `Used item: ${resp.message}`,
        });
        await refreshAuthoritativeState();
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Failed to use item';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, refreshAuthoritativeState]
  );

  const inspectConditionTreatments = useCallback(
    async (conditionId: number) => {
      if (!state.sessionToken) return;
      try {
        const resp = await apiClient.getConditionTreatments(conditionId, state.sessionToken);
        dispatch({
          type: 'SET_AVAILABLE_TREATMENTS',
          treatments: { conditionId, treatments: resp.treatments },
        });
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Failed to get treatments';
        dispatch({ type: 'SET_ERROR', error: msg });
      }
    },
    [state.sessionToken]
  );

  const treatCondition = useCallback(
    async (conditionId: number, treatmentId: string) => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.treatCondition(state.sessionToken, conditionId, treatmentId);
        dispatch({
          type: 'ADD_NARRATIVE_LOG',
          log: `Treated condition: ${resp.narrative}`,
        });
        await refreshAuthoritativeState();
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Failed to treat condition';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, refreshAuthoritativeState]
  );

  const triggerRandomEvent = useCallback(async () => {
    if (!state.sessionToken) return;
    try {
      dispatch({ type: 'SET_LOADING', loading: true });
      const event = await apiClient.triggerEvent(state.sessionToken);
      dispatch({ type: 'SET_ACTIVE_EVENT', event });
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to trigger event';
      dispatch({ type: 'SET_ERROR', error: msg });
    } finally {
      dispatch({ type: 'SET_LOADING', loading: false });
    }
  }, [state.sessionToken]);

  const resolveEventChoice = useCallback(
    async (choiceId: string) => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const res = await apiClient.chooseEvent(state.sessionToken, choiceId);
        dispatch({ type: 'SET_LAST_EVENT_RESOLUTION', resolution: res });
        dispatch({ type: 'SET_ACTIVE_EVENT', event: null });
        dispatch({ type: 'ADD_NARRATIVE_LOG', log: res.narrative });

        if (res.character_died) {
          await refreshAuthoritativeState();
          dispatch({ type: 'SET_SCREEN', screen: 'death' });
        } else {
          await refreshAuthoritativeState();
        }
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Failed to resolve event choice';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, refreshAuthoritativeState]
  );

  const startCombatEncounter = useCallback(
    async (enemyId?: string) => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const combat = await apiClient.startCombat(state.sessionToken, enemyId);
        dispatch({ type: 'SET_COMBAT_STATE', combat });
        dispatch({ type: 'SET_SCREEN', screen: 'combat' });
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Failed to initiate combat';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken]
  );

  const executeCombatAction = useCallback(
    async (
      action: 'attack' | 'defend' | 'use_skill' | 'use_item' | 'flee',
      itemId?: string
    ): Promise<CombatActionResponse> => {
      if (!state.sessionToken) throw new Error('No active session token');
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.combatAction(state.sessionToken, action, itemId);

        // Update combat state
        dispatch({
          type: 'SET_COMBAT_STATE',
          combat: {
            status: resp.status,
            turn: resp.turn,
            player_initiative: state.combatState?.player_initiative || 10,
            enemy_initiative: state.combatState?.enemy_initiative || 10,
            player_goes_first: state.combatState?.player_goes_first ?? true,
            enemy: resp.enemy,
            player: resp.player,
            combat_log: resp.combat_log,
            rewards: resp.rewards,
          },
        });

        if (resp.character_died || resp.status === 'defeat') {
          await refreshAuthoritativeState();
          dispatch({ type: 'SET_SCREEN', screen: 'death' });
        }

        return resp;
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Combat action failed';
        dispatch({ type: 'SET_ERROR', error: msg });
        throw err;
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, state.combatState, refreshAuthoritativeState]
  );

  const interactWithNpc = useCallback(
    async (npcId: number, topic?: string) => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.talkToNPC(npcId, state.sessionToken, topic);
        dispatch({
          type: 'SET_NPC_DIALOGUE',
          dialogue: { npcName: resp.npc_name, line: resp.dialogue },
        });
        dispatch({
          type: 'ADD_NARRATIVE_LOG',
          log: `Spoke with ${resp.npc_name} (${resp.relationship_tier}).`,
        });
        const profile = await apiClient.getNPCProfile(npcId, state.sessionToken);
        dispatch({ type: 'SET_SELECTED_NPC', npc: profile });
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'NPC dialogue failed';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken]
  );

  const giftNpc = useCallback(
    async (
      npcId: number,
      payload: { gold_amount?: number; item_id?: string; quantity?: number }
    ) => {
      if (!state.sessionToken) return;
      try {
        dispatch({ type: 'SET_LOADING', loading: true });
        const resp = await apiClient.giftNPC(npcId, state.sessionToken, payload);
        dispatch({
          type: 'ADD_NARRATIVE_LOG',
          log: `Gift to ${resp.npc_name}: "${resp.response_narrative}" (${resp.new_relationship_tier})`,
        });
        const profile = await apiClient.getNPCProfile(npcId, state.sessionToken);
        dispatch({ type: 'SET_SELECTED_NPC', npc: profile });
        await refreshAuthoritativeState();
      } catch (err) {
        const msg = err instanceof ApiClientError ? err.message : 'Gift to NPC failed';
        dispatch({ type: 'SET_ERROR', error: msg });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    },
    [state.sessionToken, refreshAuthoritativeState]
  );

  const concludeSession = useCallback(async () => {
    if (!state.sessionToken) return;
    try {
      dispatch({ type: 'SET_LOADING', loading: true });
      await apiClient.endSession(state.sessionToken);
      const summary = await apiClient.getSessionSummary(state.sessionToken);
      dispatch({ type: 'SET_SESSION_SUMMARY', summary });
      dispatch({ type: 'SET_SCREEN', screen: 'session_summary' });
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to conclude session';
      dispatch({ type: 'SET_ERROR', error: msg });
    } finally {
      dispatch({ type: 'SET_LOADING', loading: false });
    }
  }, [state.sessionToken]);

  const resetToMainMenu = useCallback(() => {
    dispatch({ type: 'RESET_GAME' });
  }, []);

  // Auto-restore game state if session token is in localStorage
  useEffect(() => {
    if (state.sessionToken && !state.character) {
      continueGame(state.sessionToken);
    }
  }, [state.sessionToken, state.character, continueGame]);

  const contextValue: GameContextType = {
    ...state,
    dispatch,
    goToScreen,
    setActiveTab,
    startNewGame,
    continueGame,
    refreshAuthoritativeState,
    createCharacter,
    reincarnateCharacter,
    performExplore,
    performRest,
    performWork,
    travelToLocation,
    advanceTime,
    allocateAttributePoint,
    useInventoryItem,
    treatCondition,
    inspectConditionTreatments,
    triggerRandomEvent,
    resolveEventChoice,
    startCombatEncounter,
    executeCombatAction,
    interactWithNpc,
    giftNpc,
    concludeSession,
    resetToMainMenu,
  };

  return <GameContext.Provider value={contextValue}>{children}</GameContext.Provider>;
};

export const useGame = (): GameContextType => {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
};
