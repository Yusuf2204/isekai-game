/** TypeScript types matching backend Pydantic schemas. */

export interface HealthResponse {
  status: string;
  version: string;
  service: string;
}

export interface ApiError {
  error: string;
  message: string;
  details: Record<string, unknown>;
}