/** API client for backend communication. */

import { ApiClientError, type ApiError, type HealthResponse } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

  // Health check
  async healthCheck(): Promise<HealthResponse> {
    return this.get<HealthResponse>('/api/health');
  }
}

export const apiClient = new ApiClient();
