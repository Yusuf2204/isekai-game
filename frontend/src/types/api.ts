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

export class ApiClientError extends Error {
  readonly error: string;
  readonly details: Record<string, unknown>;
  readonly status: number;

  constructor(
    message: string,
    error: string = 'API_ERROR',
    status: number = 500,
    details: Record<string, unknown> = {}
  ) {
    super(message);
    this.name = 'ApiClientError';
    this.error = error;
    this.status = status;
    this.details = details;
  }
}
