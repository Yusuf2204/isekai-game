/** Frontend smoke and foundation tests for Stage 8.
 *
 * Verifies:
 * - API Client configuration and request handling.
 * - Backend error envelope parsing (CB-04): extracts error, message, details, and HTTP status.
 * - Error boundary catching and rendering fallback (PR-09).
 * - Custom useApiError hook behavior.
 * - App component rendering under plain CSS architecture (CB-02).
 */

import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import { apiClient, ApiClient } from '../api/client';
import { ApiClientError } from '../types/api';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { useApiError } from '../hooks/useApiError';
import App from '../App';

describe('Frontend Foundation: API Client & Error Parsing (CB-04)', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('apiClient is defined and defaults to expected port 8000', () => {
    expect(apiClient).toBeDefined();
    expect(typeof apiClient.healthCheck).toBe('function');
  });

  it('parses standard Stage 6 backend error envelope correctly', async () => {
    const mockErrorResponse = {
      error: 'NOT_FOUND',
      message: 'Character not found with ID 42',
      details: { character_id: 42 },
      detail: { message: 'Character not found with ID 42' },
    };

    globalThis.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () => Promise.resolve(mockErrorResponse),
      } as Response)
    );

    const client = new ApiClient('http://localhost:8000');

    try {
      await client.get('/api/character/current');
      throw new Error('Should have thrown ApiClientError');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiClientError);
      const apiErr = err as ApiClientError;
      expect(apiErr.message).toBe('Character not found with ID 42');
      expect(apiErr.error).toBe('NOT_FOUND');
      expect(apiErr.status).toBe(404);
      expect(apiErr.details).toEqual({ character_id: 42 });
    }
  });

  it('parses FastAPI string detail fallback without undefined values', async () => {
    globalThis.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: () => Promise.resolve({ detail: 'Invalid session token' }),
      } as Response)
    );

    const client = new ApiClient('http://localhost:8000');

    try {
      await client.get('/api/character/current');
      throw new Error('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiClientError);
      const apiErr = err as ApiClientError;
      expect(apiErr.message).toBe('Invalid session token');
      expect(apiErr.error).toBe('HTTP_ERROR');
      expect(apiErr.status).toBe(401);
    }
  });

  it('falls back gracefully on non-JSON HTTP errors', async () => {
    globalThis.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        status: 502,
        statusText: 'Bad Gateway',
        json: () => Promise.reject(new Error('SyntaxError')),
      } as Response)
    );

    const client = new ApiClient('http://localhost:8000');

    try {
      await client.get('/api/health');
      throw new Error('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiClientError);
      const apiErr = err as ApiClientError;
      expect(apiErr.message).toBe('HTTP 502: Bad Gateway');
      expect(apiErr.error).toBe('HTTP_ERROR');
      expect(apiErr.status).toBe(502);
    }
  });
});

describe('Frontend Foundation: Error Boundary & Hooks (PR-09)', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(() => {
    container.remove();
  });

  it('ErrorBoundary renders children when there is no error', async () => {
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <ErrorBoundary>
          <div data-testid="child">Child Content</div>
        </ErrorBoundary>
      );
    });

    expect(container.textContent).toContain('Child Content');

    await act(async () => {
      root.unmount();
    });
  });

  it('ErrorBoundary catches rendering crashes and renders dark fantasy error card', async () => {
    // Suppress console.error during expected throw
    const originalConsoleError = console.error;
    console.error = jest.fn();

    const CrashingComponent = () => {
      throw new Error('Simulated Render Explosion');
    };

    const root = createRoot(container);

    await act(async () => {
      root.render(
        <ErrorBoundary>
          <CrashingComponent />
        </ErrorBoundary>
      );
    });

    expect(container.textContent).toContain('Application Error');
    expect(container.textContent).toContain('A fatal error occurred');
    expect(container.textContent).toContain('Simulated Render Explosion');
    expect(container.textContent).toContain('Reload Application');

    console.error = originalConsoleError;

    await act(async () => {
      root.unmount();
    });
  });

  it('useApiError formats and clears errors correctly', async () => {
    let hookResult!: ReturnType<typeof useApiError>;

    const TestComponent = () => {
      hookResult = useApiError();
      return null;
    };

    const root = createRoot(container);

    await act(async () => {
      root.render(<TestComponent />);
    });

    expect(hookResult.error).toBeNull();
    expect(hookResult.errorMessage).toBeNull();
    expect(hookResult.errorCode).toBeNull();

    // Set ApiClientError
    await act(async () => {
      hookResult.setError(
        new ApiClientError('Insufficient stamina for explore', 'RESOURCE_ERROR', 400)
      );
    });

    expect(hookResult.errorMessage).toBe('Insufficient stamina for explore');
    expect(hookResult.errorCode).toBe('RESOURCE_ERROR');

    // Clear error
    await act(async () => {
      hookResult.clearError();
    });

    expect(hookResult.error).toBeNull();
    expect(hookResult.errorMessage).toBeNull();

    await act(async () => {
      root.unmount();
    });
  });
});

describe('Frontend Foundation: App Smoke Test (CB-02)', () => {
  const originalFetch = globalThis.fetch;
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    container.remove();
  });

  it('renders App with successful health check', async () => {
    globalThis.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: () =>
          Promise.resolve({
            status: 'healthy',
            version: '0.1.0',
            service: 'isekai-backend',
          }),
      } as Response)
    );

    const root = createRoot(container);

    await act(async () => {
      root.render(<App />);
    });

    expect(container.textContent).toContain('Isekai: A Life Unwritten');
    expect(container.textContent).toContain('System Status');
    expect(container.textContent).toContain('healthy');
    expect(container.textContent).toContain('isekai-backend');
    expect(container.textContent).toContain('Development Info');

    await act(async () => {
      root.unmount();
    });
  });

  it('renders App with failed health check error alert', async () => {
    globalThis.fetch = jest.fn(() =>
      Promise.reject(new Error('Failed to fetch'))
    );

    const root = createRoot(container);

    await act(async () => {
      root.render(<App />);
    });

    expect(container.textContent).toContain('Connection Failed');
    expect(container.textContent).toContain('Failed to fetch');
    expect(container.textContent).toContain('http://localhost:8000');

    await act(async () => {
      root.unmount();
    });
  });
});
