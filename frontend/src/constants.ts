/** Application constants and API configuration.
 *
 * Centralizes UI constants, default port settings, and endpoints
 * as mandated by AGENTS.md §2.
 */

export const DEFAULT_API_BASE_URL = 'http://localhost:8000';
export const API_PORT = 8000;
export const DEV_SERVER_PORT = 5173;

export const APP_TITLE = 'Isekai: A Life Unwritten';
export const APP_VERSION = '0.1.0';

export const API_ENDPOINTS = {
  HEALTH: '/api/health',
  CHARACTER: {
    CREATE: '/api/character/create',
    CURRENT: '/api/character/current',
    ATTRIBUTES: '/api/character/attributes',
    SKILLS: '/api/character/skills',
    RESOURCES: '/api/character/resources',
    PROGRESSION: '/api/character/progression',
  },
  WORLD: {
    KINGDOM: '/api/world/kingdom',
    REGIONS: '/api/world/regions',
    LOCATIONS: '/api/world/locations',
    CURRENT_LOCATION: '/api/world/locations/current',
    TRAVEL: '/api/world/locations/travel',
  },
  TIME: {
    PERIODS: '/api/time/periods',
    ADVANCE: '/api/time/advance',
  },
  ACTIVITIES: {
    EXPLORE: '/api/activities/explore',
    REST: '/api/activities/rest',
    WORK: '/api/activities/work',
  },
  CONDITIONS: {
    LIST: '/api/conditions/',
    DEFINITIONS: '/api/conditions/definitions',
    TREATMENTS: '/api/conditions/treatments',
    CONDITION_TREATMENTS: (id: number) => `/api/conditions/${id}/treatments`,
    TREAT: '/api/conditions/treat',
  },
  INVENTORY: {
    LIST: '/api/inventory/',
    USE: '/api/inventory/use',
  },
} as const;
