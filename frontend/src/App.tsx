/** Main App component. */

import { useEffect, useState } from 'react';
import { apiClient } from './api/client';
import type { HealthResponse } from './types/api';

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const response = await apiClient.healthCheck();
        if (isMounted) {
          setHealth(response);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    checkHealth();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="container">
          <div className="app-header-inner">
            <h1 className="app-title">Isekai: A Life Unwritten</h1>
            <span className="app-version">v0.1.0</span>
          </div>
        </div>
      </header>

      <main className="app-main container">
        <section className="app-content">
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">System Status</h2>
            </div>

            <div className="card-stack">
              {loading && (
                <div className="loading-box" role="status" aria-live="polite">
                  <div className="spinner" aria-hidden="true" />
                  <span>Checking backend connection...</span>
                </div>
              )}

              {error && (
                <div className="alert alert-error" role="alert">
                  <p className="alert-title">Connection Failed</p>
                  <p className="alert-message">{error}</p>
                  <p className="alert-hint">
                    Make sure the backend is running on <code>http://localhost:8000</code>
                  </p>
                </div>
              )}

              {health && !loading && (
                <div className="status-grid">
                  <div className="status-item">
                    <span className="status-label">Status</span>
                    <span
                      className={`status-value ${
                        health.status === 'healthy' ? 'status-healthy' : 'status-unhealthy'
                      }`}
                    >
                      {health.status}
                    </span>
                  </div>
                  <div className="status-item">
                    <span className="status-label">Version</span>
                    <span className="status-value text-mono">{health.version}</span>
                  </div>
                  <div className="status-item">
                    <span className="status-label">Service</span>
                    <span className="status-value text-mono">{health.service}</span>
                  </div>
                </div>
              )}

              {!loading && !error && !health && (
                <p className="text-muted">No response from backend</p>
              )}
            </div>
          </div>

          <div className="mt-8 card">
            <div className="card-header">
              <h2 className="card-title">Development Info</h2>
            </div>
            <div className="dev-info-list">
              <p>
                <strong>Frontend:</strong> React 18 + TypeScript + Vite
              </p>
              <p>
                <strong>Backend:</strong> FastAPI + SQLAlchemy + SQLite
              </p>
              <p>
                <strong>API Base:</strong>{' '}
                <code>{import.meta.env.VITE_API_URL || 'http://localhost:8000'}</code>
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="app-footer">
        <div className="container">
          <p className="app-footer-text">
            Isekai: A Life Unwritten &mdash; Dark Fantasy Text RPG
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
