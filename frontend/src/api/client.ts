/** API client for backend communication.
 *
 * Implements authoritative backend contract per AGENTS.md §2 & §3.
 */

import { ApiClientError, type ApiError, type HealthResponse } from '../types/api';
import type {
  ActivityListResponse,
  AdvanceTimeResponse,
  AllRelationshipsResponse,
  AttributeAllocateRequest,
  AttributeAllocateResponse,
  AttributePointsResponse,
  AvailableTreatmentsResponse,
  BackgroundSummary,
  Character,
  CharacterCreateRequest,
  CharacterCreateResponse,
  CharacterInventoryItem,
  CharacterLegacy,
  CombatActionResponse,
  CombatState,
  ConditionItem,
  EventResolutionResponse,
  ExploreResponse,
  LifeRecord,
  LocationDetailResponse,
  LocationSummary,
  NPCDetail,
  NPCGiftResponse,
  NPCSummary,
  NPCTalkResponse,
  RaceSummary,
  ReincarnateRequest,
  ReincarnationStatusResponse,
  ResourceStatus,
  RestResponse,
  SessionHistoryResponse,
  SessionSummaryResponse,
  TimeState,
  TravelResponse,
  TreatmentResponse,
  UnifiedProgressionStatus,
  WorkResponse,
  ActiveEvent,
} from '../types/game';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      let message = `HTTP ${response.status}: ${response.statusText}`;
      let errorCode = 'HTTP_ERROR';
      let details: Record<string, unknown> = {};

      try {
        const raw: unknown = await response.json();
        if (raw && typeof raw === 'object') {
          const payload = raw as Partial<ApiError> & { detail?: unknown };

          // Standard backend error envelope (Stage 6)
          if (typeof payload.message === 'string' && payload.message.trim()) {
            message = payload.message;
          } else if (typeof payload.detail === 'string' && payload.detail.trim()) {
            // Standard FastAPI HTTP exception detail string
            message = payload.detail;
          } else if (
            payload.detail &&
            typeof payload.detail === 'object' &&
            'message' in payload.detail &&
            typeof (payload.detail as { message: unknown }).message === 'string'
          ) {
            message = (payload.detail as { message: string }).message;
          }

          if (typeof payload.error === 'string' && payload.error.trim()) {
            errorCode = payload.error;
          }

          if (
            payload.details &&
            typeof payload.details === 'object' &&
            !Array.isArray(payload.details)
          ) {
            details = payload.details as Record<string, unknown>;
          }
        }
      } catch {
        // Fallback to default message when response is not JSON
      }

      throw new ApiClientError(message, errorCode, response.status, details);
    }

    return response.json() as Promise<T>;
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data !== undefined ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data !== undefined ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // --- Health ---
  async healthCheck(): Promise<HealthResponse> {
    return this.get<HealthResponse>('/api/health');
  }

  // --- Character & Creation ---
  async getRaces(): Promise<RaceSummary[]> {
    return this.get<RaceSummary[]>('/api/character/races');
  }

  async getBackgrounds(): Promise<BackgroundSummary[]> {
    return this.get<BackgroundSummary[]>('/api/character/backgrounds');
  }

  async getCurrentCharacter(sessionToken: string): Promise<Character> {
    return this.get<Character>(`/api/character/current?session_token=${encodeURIComponent(sessionToken)}`);
  }

  async createCharacter(request: CharacterCreateRequest): Promise<CharacterCreateResponse> {
    return this.post<CharacterCreateResponse>('/api/character/create', request);
  }

  async allocateAttribute(
    sessionToken: string,
    request: AttributeAllocateRequest
  ): Promise<AttributeAllocateResponse> {
    return this.post<AttributeAllocateResponse>(
      `/api/character/allocate-attribute?session_token=${encodeURIComponent(sessionToken)}`,
      request
    );
  }

  async getAttributePoints(sessionToken: string): Promise<AttributePointsResponse> {
    return this.get<AttributePointsResponse>(
      `/api/character/attribute-points?session_token=${encodeURIComponent(sessionToken)}`
    );
  }

  async getProgression(sessionToken: string): Promise<UnifiedProgressionStatus> {
    return this.get<UnifiedProgressionStatus>(
      `/api/character/progression?session_token=${encodeURIComponent(sessionToken)}`
    );
  }

  async getResources(sessionToken: string): Promise<ResourceStatus> {
    return this.get<ResourceStatus>(
      `/api/character/resources?session_token=${encodeURIComponent(sessionToken)}`
    );
  }

  // --- World & Locations ---
  async getLocations(regionId?: number, locationType?: string): Promise<{ total: number; locations: LocationSummary[] }> {
    const params = new URLSearchParams();
    if (regionId !== undefined) params.append('region_id', regionId.toString());
    if (locationType) params.append('location_type', locationType);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.get<{ total: number; locations: LocationSummary[] }>(`/api/world/locations${qs}`);
  }

  async getLocationDetail(locationId: number): Promise<LocationDetailResponse> {
    return this.get<LocationDetailResponse>(`/api/world/locations/${locationId}`);
  }

  async travel(sessionToken: string, destinationId: number): Promise<TravelResponse> {
    return this.post<TravelResponse>('/api/world/travel', {
      session_token: sessionToken,
      destination_id: destinationId,
    });
  }

  // --- Time System ---
  async getTimeState(sessionToken: string): Promise<TimeState> {
    return this.get<TimeState>(`/api/time/state?session_token=${encodeURIComponent(sessionToken)}`);
  }

  async advanceTime(sessionToken: string, periods: number): Promise<AdvanceTimeResponse> {
    return this.post<AdvanceTimeResponse>('/api/time/advance', {
      session_token: sessionToken,
      periods,
    });
  }

  // --- Activities ---
  async getAvailableActivities(sessionToken: string): Promise<ActivityListResponse> {
    return this.get<ActivityListResponse>(
      `/api/activities/available?session_token=${encodeURIComponent(sessionToken)}`
    );
  }

  async explore(sessionToken: string, locationId?: number): Promise<ExploreResponse> {
    return this.post<ExploreResponse>('/api/activities/explore', {
      session_token: sessionToken,
      location_id: locationId,
    });
  }

  async rest(sessionToken: string, restType: 'short' | 'long'): Promise<RestResponse> {
    return this.post<RestResponse>('/api/activities/rest', {
      session_token: sessionToken,
      rest_type: restType,
    });
  }

  async work(sessionToken: string, workType: string, locationId?: number): Promise<WorkResponse> {
    return this.post<WorkResponse>('/api/activities/work', {
      session_token: sessionToken,
      work_type: workType,
      location_id: locationId,
    });
  }

  // --- Inventory ---
  async getInventory(sessionToken: string): Promise<{ items: CharacterInventoryItem[]; total_items: number }> {
    return this.get<{ items: CharacterInventoryItem[]; total_items: number }>(
      `/api/inventory/inventory?session_token=${encodeURIComponent(sessionToken)}`
    );
  }

  async useItem(
    sessionToken: string,
    itemId: string,
    quantity: number = 1
  ): Promise<{ success: boolean; message: string; remaining_quantity: number }> {
    return this.post<{ success: boolean; message: string; remaining_quantity: number }>(
      '/api/inventory/inventory/use',
      {
        session_token: sessionToken,
        item_id: itemId,
        quantity,
      }
    );
  }

  // --- Conditions & Treatments ---
  async getConditions(sessionToken: string): Promise<{ conditions: ConditionItem[]; total_conditions: number }> {
    return this.get<{ conditions: ConditionItem[]; total_conditions: number }>(
      `/api/conditions/?session_token=${encodeURIComponent(sessionToken)}`
    );
  }

  async getConditionTreatments(
    conditionId: number,
    sessionToken: string
  ): Promise<AvailableTreatmentsResponse> {
    return this.get<AvailableTreatmentsResponse>(
      `/api/conditions/${conditionId}/treatments?session_token=${encodeURIComponent(sessionToken)}`
    );
  }

  async treatCondition(
    sessionToken: string,
    conditionId: number,
    treatmentId: string
  ): Promise<TreatmentResponse> {
    return this.post<TreatmentResponse>('/api/conditions/treat', {
      session_token: sessionToken,
      condition_id: conditionId,
      treatment_id: treatmentId,
    });
  }

  // --- Events ---
  async getActiveEvent(sessionToken: string): Promise<ActiveEvent | null> {
    const resp = await this.get<{
      has_active_event: boolean;
      event: (ActiveEvent & { id?: string; description?: string }) | null;
    }>(`/api/events/active?session_token=${encodeURIComponent(sessionToken)}`);
    if (!resp || !resp.has_active_event || !resp.event) return null;
    return {
      ...resp.event,
      event_id: resp.event.event_id || resp.event.id || '',
      narrative: resp.event.narrative || resp.event.description || '',
      choices: resp.event.choices || [],
    };
  }

  async triggerEvent(
    sessionToken: string,
    eventId?: string,
    forceTrigger: boolean = false
  ): Promise<ActiveEvent | null> {
    const resp = await this.post<{
      has_active_event: boolean;
      event: (ActiveEvent & { id?: string; description?: string }) | null;
    }>('/api/events/trigger', {
      session_token: sessionToken,
      event_id: eventId,
      force_trigger: forceTrigger,
    });
    if (!resp || !resp.has_active_event || !resp.event) return null;
    return {
      ...resp.event,
      event_id: resp.event.event_id || resp.event.id || '',
      narrative: resp.event.narrative || resp.event.description || '',
      choices: resp.event.choices || [],
    };
  }

  async chooseEvent(sessionToken: string, choiceId: string): Promise<EventResolutionResponse> {
    return this.post<EventResolutionResponse>('/api/events/choose', {
      session_token: sessionToken,
      choice_id: choiceId,
    });
  }

  // --- Combat ---
  async startCombat(sessionToken: string, enemyId?: string): Promise<CombatState> {
    return this.post<CombatState>('/api/combat/start', {
      session_token: sessionToken,
      enemy_id: enemyId,
    });
  }

  async getCombatState(sessionToken: string): Promise<CombatState> {
    return this.get<CombatState>(`/api/combat/state?session_token=${encodeURIComponent(sessionToken)}`);
  }

  async combatAction(
    sessionToken: string,
    action: 'attack' | 'defend' | 'use_skill' | 'use_item' | 'flee',
    itemId?: string
  ): Promise<CombatActionResponse> {
    return this.post<CombatActionResponse>('/api/combat/action', {
      session_token: sessionToken,
      action,
      item_id: itemId,
    });
  }

  // --- NPCs ---
  async getNPCsAtLocation(
    locationId: number,
    sessionToken: string
  ): Promise<{ location_id: number; location_name: string; npcs: NPCSummary[]; total: number }> {
    return this.get<{ location_id: number; location_name: string; npcs: NPCSummary[]; total: number }>(
      `/api/npc/location/${locationId}?session_token=${encodeURIComponent(sessionToken)}`
    );
  }

  async getNPCProfile(npcId: number, sessionToken: string): Promise<NPCDetail> {
    return this.get<NPCDetail>(`/api/npc/${npcId}?session_token=${encodeURIComponent(sessionToken)}`);
  }

  async talkToNPC(npcId: number, sessionToken: string, topic?: string): Promise<NPCTalkResponse> {
    return this.post<NPCTalkResponse>(`/api/npc/${npcId}/talk`, {
      session_token: sessionToken,
      topic,
    });
  }

  async giftNPC(
    npcId: number,
    sessionToken: string,
    payload: { gold_amount?: number; item_id?: string; quantity?: number }
  ): Promise<NPCGiftResponse> {
    return this.post<NPCGiftResponse>(`/api/npc/${npcId}/gift`, {
      session_token: sessionToken,
      ...payload,
    });
  }

  async getNPCRelationships(sessionToken: string): Promise<AllRelationshipsResponse> {
    return this.get<AllRelationshipsResponse>(
      `/api/npc/relationships?session_token=${encodeURIComponent(sessionToken)}`
    );
  }

  // --- Reincarnation & Death ---
  async getReincarnationStatus(sessionToken: string): Promise<ReincarnationStatusResponse> {
    return this.get<ReincarnationStatusResponse>(
      `/api/reincarnation/status?session_token=${encodeURIComponent(sessionToken)}`
    );
  }

  async getLifeRecord(characterId: number): Promise<LifeRecord> {
    return this.get<LifeRecord>(`/api/reincarnation/life-record/${characterId}`);
  }

  async getLegacy(characterId: number): Promise<CharacterLegacy> {
    return this.get<CharacterLegacy>(`/api/reincarnation/legacy/${characterId}`);
  }

  async reincarnate(request: ReincarnateRequest): Promise<CharacterCreateResponse> {
    return this.post<CharacterCreateResponse>('/api/reincarnation/reincarnate', request);
  }

  // --- Session & History ---
  async getSessionSummary(sessionToken: string): Promise<SessionSummaryResponse> {
    return this.get<SessionSummaryResponse>(
      `/api/session/summary?session_token=${encodeURIComponent(sessionToken)}`
    );
  }

  async endSession(
    sessionToken: string
  ): Promise<{ message: string; session_id: number; characters_retired: number }> {
    return this.post<{ message: string; session_id: number; characters_retired: number }>(
      '/api/session/end',
      { session_token: sessionToken }
    );
  }

  async getSessionHistory(): Promise<SessionHistoryResponse> {
    return this.get<SessionHistoryResponse>('/api/session/history');
  }
}

export const apiClient = new ApiClient();
