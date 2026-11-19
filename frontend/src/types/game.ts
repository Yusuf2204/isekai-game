/** TypeScript types matching backend domain and schema representations.
 *
 * Implements strict types as required by AGENTS.md §2 & §3.
 */

// --- Character & Creation ---

export interface CharacterAttribute {
  name: string;
  base_value: number;
  current_value: number;
  experience: number;
}

export interface CharacterSkill {
  name: string;
  level: number;
  experience: number;
}

export interface CharacterInventoryItem {
  item_id: string;
  name: string;
  description: string;
  quantity: number;
  item_type: string;
  value: number;
  is_equipped: boolean;
  properties: Record<string, unknown>;
}

export interface Character {
  id: number;
  session_id: number;
  generation: number;
  name: string;
  race_name: string;
  background_name: string;
  gender_presentation: string;
  age: number;
  personality_trait: string;
  personality_description: string;
  starting_location_id: number | null;
  legacy_id: number | null;
  is_alive: boolean;
  current_health: number;
  max_health: number;
  money: number;
  reputation: number;
  noble_favor: number;
  common_favor: number;
  attribute_points: number;
  attributes: CharacterAttribute[];
  skills: CharacterSkill[];
  inventory: CharacterInventoryItem[];
}

export interface RaceSummary {
  name: string;
  display_name: string;
  description: string;
  lore: string;
  strength_modifier: number;
  agility_modifier: number;
  intelligence_modifier: number;
  vitality_modifier: number;
  luck_modifier: number;
  racial_trait_name: string;
  racial_trait_description: string;
}

export interface BackgroundSummary {
  name: string;
  display_name: string;
  description: string;
  starting_money: number;
  starting_skills: Record<string, number>;
}

export interface CharacterCreateRequest {
  name: string;
  race_name: string;
  background_name: string;
  gender_presentation: string;
  starting_location_id?: number | null;
  session_token?: string | null;
}

export interface CharacterCreateResponse {
  character: Character;
  session_token: string;
  message: string;
}

// --- Progression & Resources ---

export interface AttributeAllocateRequest {
  attribute_name: string;
  points: number;
}

export interface AttributeAllocateResponse {
  attribute_name: string;
  points_allocated: number;
  previous_value: number;
  new_value: number;
  remaining_points: number;
  message: string;
}

export interface AttributePointsResponse {
  attribute_points: number;
}

export interface SkillProgression {
  name: string;
  level: number;
  experience: number;
  experience_for_next_level: number;
  progress_percent: number;
}

export interface AttributeProgression {
  name: string;
  base_value: number;
  current_value: number;
  experience: number;
}

export interface CharacterProgression {
  level: number;
  experience: number;
  experience_for_next_level: number;
  progress_percent: number;
  attribute_points: number;
}

export interface UnifiedProgressionStatus {
  character: CharacterProgression;
  skills: SkillProgression[];
  attributes: AttributeProgression[];
}

export interface ResourceStatus {
  health: {
    current: number;
    max: number;
    percent: number;
  };
  stamina: {
    current: number;
    max: number;
    effective_max: number;
    percent: number;
  };
  fatigue: {
    level: number;
    max: number;
    percent: number;
  };
  is_alive: boolean;
  money: number;
  penalties: {
    stamina_penalty: number;
    attribute_penalties: Record<string, number>;
  };
}

// --- World & Locations ---

export interface LocationSummary {
  id: number;
  name: string;
  description: string;
  region_name: string;
  location_type: string;
  danger_level: number;
  population: number;
  has_guild: boolean;
  has_market: boolean;
  has_inn: boolean;
  available_activities: string[];
}

export interface RegionSummary {
  id: number;
  name: string;
  display_name: string;
  description: string;
  danger_level: number;
}

export interface WorldOverviewResponse {
  kingdom_name: string;
  kingdom_description: string;
  regions: RegionSummary[];
  total_locations: number;
}

export interface LocationDetailResponse {
  location: LocationSummary;
  region: RegionSummary;
  npcs: Array<{
    id: number;
    name: string;
    race_name: string;
    occupation: string;
    personality: string;
    description: string;
  }>;
}

export interface TravelResponse {
  success: boolean;
  message: string;
  destination: LocationSummary;
  time_elapsed_periods: number;
  current_time: {
    day: number;
    time_of_day: string;
  };
}

// --- Time System ---

export interface TimeState {
  current_day: number;
  current_time_of_day: string;
  total_periods_elapsed: number;
  is_daytime: boolean;
}

export interface AdvanceTimeResponse {
  previous_time: TimeState;
  current_time: TimeState;
  periods_advanced: number;
  days_advanced: number;
  expired_conditions: string[];
}

// --- Activities ---

export interface ActivityOption {
  name: string;
  display_name: string;
  description: string;
  stamina_cost: number;
  time_cost_periods: number;
  is_available: boolean;
  unavailable_reason?: string | null;
}

export interface ActivityListResponse {
  activities: ActivityOption[];
  location_name: string;
  current_time_of_day: string;
  current_day: number;
  stamina_available: number;
}

export interface ExploreResponse {
  narrative: string;
  money_change: number;
  items_found: CharacterInventoryItem[];
  survival_xp_gained: number;
  character_xp_gained: number;
  health_change: number;
  stamina_cost: number;
  time_cost_periods: number;
  current_time: TimeState;
  level_up_occurred: boolean;
}

export interface RestResponse {
  narrative: string;
  rest_type: 'short' | 'long';
  health_restored: number;
  stamina_restored: number;
  fatigue_reduced: number;
  was_interrupted: boolean;
  time_cost_periods: number;
  current_time: TimeState;
}

export interface WorkResponse {
  narrative: string;
  work_type: string;
  wages_earned: number;
  skill_xp_gained: number;
  skill_trained: string;
  character_xp_gained: number;
  stamina_cost: number;
  time_cost_periods: number;
  current_time: TimeState;
  level_up_occurred: boolean;
}

// --- Events System ---

export interface StatCheckResult {
  attribute: string;
  roll: number;
  modifier: number;
  total: number;
  dc: number;
  success: boolean;
}

export interface EventChoiceOption {
  id: string;
  label: string;
  description: string;
  stat_check?: {
    attribute: string;
    dc: number;
  } | null;
}

export interface ActiveEvent {
  event_id: string;
  title: string;
  narrative: string;
  category: string;
  choices: EventChoiceOption[];
}

export interface EventResolutionResponse {
  event_id: string;
  choice_id: string;
  narrative: string;
  stat_check_result?: StatCheckResult | null;
  outcome_success: boolean;
  deltas: {
    health?: number;
    stamina?: number;
    money?: number;
    skill_xp?: Record<string, number>;
    attributes?: Record<string, number>;
  };
  character_died: boolean;
  death_cause?: string | null;
}

// --- Combat System ---

export interface CombatEnemy {
  id: string;
  name: string;
  enemy_type: string;
  level: number;
  current_health: number;
  max_health: number;
  attack_power: number;
  defense: number;
  agility: number;
  description: string;
}

export interface CombatPlayerStatus {
  current_health: number;
  max_health: number;
  current_stamina: number;
  max_stamina: number;
  level: number;
}

export interface CombatState {
  status: 'active' | 'victory' | 'defeat' | 'fled';
  turn: number;
  player_initiative: number;
  enemy_initiative: number;
  player_goes_first: boolean;
  enemy: CombatEnemy;
  player: CombatPlayerStatus;
  combat_log: string[];
  rewards?: {
    character_xp: number;
    skill_xp: Record<string, number>;
    money: number;
    loot: CharacterInventoryItem[];
  } | null;
}

export interface CombatActionResponse {
  status: 'active' | 'victory' | 'defeat' | 'fled';
  turn: number;
  player: CombatPlayerStatus;
  enemy: CombatEnemy;
  combat_log: string[];
  rewards?: {
    character_xp: number;
    skill_xp: Record<string, number>;
    money: number;
    loot: CharacterInventoryItem[];
  } | null;
  character_died: boolean;
  death_cause?: string | null;
}

// --- NPC Interaction ---

export interface NPCSummary {
  id: number;
  name: string;
  race_name: string;
  occupation: string;
  personality: string;
  location_id: number;
  location_name: string;
  relationship_value: number;
  trust_level: number;
  relationship_tier: string;
}

export interface NPCDetail {
  id: number;
  name: string;
  race_name: string;
  occupation: string;
  personality: string;
  location_id: number;
  location_name: string;
  description: string;
  relationship_value: number;
  trust_level: number;
  relationship_tier: string;
  topics: string[];
  memory_flags: Record<string, boolean>;
}

export interface NPCTalkResponse {
  npc_name: string;
  dialogue: string;
  relationship_value: number;
  relationship_tier: string;
  trust_level: number;
  topic_discussed?: string | null;
}

export interface NPCGiftResponse {
  npc_name: string;
  response_narrative: string;
  relationship_change: number;
  trust_change: number;
  new_relationship_value: number;
  new_trust_level: number;
  new_relationship_tier: string;
}

export interface NPCRelationshipSummary {
  npc_id: number;
  npc_name: string;
  occupation: string;
  location_name: string;
  relationship_value: number;
  trust_level: number;
  relationship_tier: string;
}

export interface AllRelationshipsResponse {
  relationships: NPCRelationshipSummary[];
  total: number;
}

// --- Conditions & Treatments ---

export interface ConditionItem {
  id: number;
  name: string;
  display_name: string;
  condition_type: string;
  severity: number;
  duration_remaining: number;
  description: string;
}

export interface TreatmentItem {
  id: string;
  name: string;
  description: string;
  cost_money: number;
  required_item_id?: string | null;
  recovery_amount: number;
}

export interface AvailableTreatmentsResponse {
  condition_id: number;
  condition_name: string;
  treatments: TreatmentItem[];
}

export interface TreatmentResponse {
  condition_id: number;
  condition_name: string;
  cured: boolean;
  severity_reduction: number;
  narrative: string;
}

// --- Reincarnation & Death ---

export interface CharacterLegacy {
  id: number;
  character_id: number;
  bonus_attribute: string | null;
  bonus_attribute_value: number;
  skill_affinity: string | null;
  skill_affinity_bonus: number;
  money_bonus: number;
  personality_memory: string;
  unlocked_at_generation: number;
}

export interface LifeRecord {
  id: number;
  character_id: number;
  character_name: string;
  generation: number;
  race: string;
  background: string;
  age_at_death: number;
  days_lived: number;
  death_cause: string;
  obituary: string;
  final_attributes: Record<string, number>;
  final_skills: Record<string, number>;
  final_money: number;
  achievements: string[];
  legacy_id?: number | null;
}

export interface ReincarnationStatusResponse {
  is_alive: boolean;
  can_reincarnate: boolean;
  current_generation: number;
  current_character_id: number | null;
  deceased_character_id: number | null;
  legacy_available: boolean;
  legacy_preview?: CharacterLegacy | null;
  message: string;
}

export interface ReincarnateRequest {
  session_token: string;
  name: string;
  race_name: string;
  background_name: string;
  gender_presentation: string;
  starting_location_id?: number | null;
}

// --- Session & History ---

export interface SessionSummaryCharacter {
  id: number;
  generation: number;
  name: string;
  race_name: string;
  background_name: string;
  is_alive: boolean;
  age: number;
  days_lived: number;
  money: number;
  death_cause?: string | null;
  obituary?: string | null;
  legacy_left?: CharacterLegacy | null;
  legacy_inherited?: CharacterLegacy | null;
  achievements: string[];
}

export interface SessionSummaryResponse {
  session_id: number;
  session_token: string;
  is_active: boolean;
  current_generation: number;
  total_characters: number;
  total_days_lived: number;
  total_achievements: number;
  characters: SessionSummaryCharacter[];
}

export interface SessionHistoryItem {
  id: number;
  session_token: string;
  is_active: boolean;
  current_generation: number;
  created_at: string;
  total_characters: number;
  character_names: string[];
}

export interface SessionHistoryResponse {
  total: number;
  sessions: SessionHistoryItem[];
}
