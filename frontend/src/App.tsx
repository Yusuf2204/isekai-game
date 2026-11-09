/** Main App component. */

import { useEffect, useState } from 'react';
import { apiClient } from './api/client';
import type { HealthResponse } from './types/api';

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await apiClient.healthCheck();
        setHealth(response);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)]">
        <div className="container">
          <div className="flex items-center justify-between h-[var(--header-height)]">
            <h1 className="font-display text-xl font-semibold text-[var(--color-accent-gold)]">
              Isekai: A Life Unwritten
            </h1>
            <span className="text-sm text-[var(--color-text-muted)]">v0.1.0</span>
          </div>
        </div>
      </header>

      <main className="flex-1 container py-8">
        <section className="max-w-2xl mx-auto">
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">System Status</h2>
            </div>

            <div className="space-y-4">
              {loading && (
                <div className="flex items-center gap-3 text-[var(--color-text-secondary)]">
                  <div className="w-5 h-5 border-2 border-[var(--color-accent-gold)] border-t-transparent rounded-full animate-spin" />
                  <span>Checking backend connection...</span>
                </div>
              )}

              {error && (
                <div className="p-4 bg-[var(--color-accent-crimson-dark)] border border-[var(--color-accent-crimson)] rounded-md">
                  <p className="text-[var(--color-accent-crimson-light)] font-medium">Connection Failed</p>
                  <p className="text-sm text-[var(--color-text-secondary)] mt-1">{error}</p>
                  <p className="text-xs text-[var(--color-text-muted)] mt-2">
                    Make sure the backend is running on <code>http://localhost:8000</code>
                  </p>
                </div>
              )}

              {health && !loading && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-[var(--color-bg-tertiary)] rounded-md">
                    <span className="text-[var(--color-text-secondary)]">Status</span>
                    <span className={`font-medium ${
                      health.status === 'healthy' ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'
                    }`}>
                      {health.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-[var(--color-bg-tertiary)] rounded-md">
                    <span className="text-[var(--color-text-secondary)]">Version</span>
                    <span className="font-mono text-[var(--color-text-primary)]">{health.version}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-[var(--color-bg-tertiary)] rounded-md">
                    <span className="text-[var(--color-text-secondary)]">Service</span>
                    <span className="font-mono text-[var(--color-text-primary)]">{health.service}</span>
                  </div>
                </div>
              )}

              {!loading && !error && !health && (
                <p className="text-[var(--color-text-muted)]">No response from backend</p>
              )}
            </div>
          </div>

          <div className="mt-8 card">
            <div className="card-header">
              <h2 className="card-title">Development Info</h2>
            </div>
            <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
              <p><strong>Frontend:</strong> React 18 + TypeScript + Vite</p>
              <p><strong>Backend:</strong> FastAPI + SQLAlchemy + SQLite</p>
              <p><strong>API Base:</strong> <code className="text-[var(--color-text-muted)]">{import.meta.env.VITE_API_URL || 'http://localhost:8000'}</code></p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)]">
        <div className="container py-4">
          <p className="text-center text-sm text-[var(--color-text-muted)]">
            Isekai: A Life Unwritten &mdash; Dark Fantasy Text RPG
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;