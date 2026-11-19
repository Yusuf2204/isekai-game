/** Main App component with GameProvider and Screen Routing.
 *
 * Implements SPEC §12 and AGENTS.md §1:
 * - React Context + useReducer for authoritative state
 * - Screen routing across MainMenu, CharacterCreation, Gameplay, Combat, Death, SessionSummary, History
 * - System status, error boundary, and backend connectivity
 */

import React, { useEffect, useState } from 'react';
import { apiClient } from './api/client';
import { GameProvider, useGame } from './context/GameContext';
import { CharacterCreationScreen } from './screens/CharacterCreationScreen';
import { CombatScreen } from './screens/CombatScreen';
import { DeathReincarnationScreen } from './screens/DeathReincarnationScreen';
import { GameplayScreen } from './screens/GameplayScreen';
import { MainMenuScreen } from './screens/MainMenuScreen';
import { SessionHistoryScreen } from './screens/SessionHistoryScreen';
import { SessionSummaryScreen } from './screens/SessionSummaryScreen';
import type { HealthResponse } from './types/api';

const ScreenRouter: React.FC = () => {
  const { currentScreen } = useGame();

  switch (currentScreen) {
    case 'character_creation':
      return <CharacterCreationScreen />;
    case 'gameplay':
      return <GameplayScreen />;
    case 'combat':
      return <CombatScreen />;
    case 'death':
      return <DeathReincarnationScreen />;
    case 'session_summary':
      return <SessionSummaryScreen />;
    case 'history':
      return <SessionHistoryScreen />;
    case 'main_menu':
    default:
      return <MainMenuScreen />;
  }
};

const AppContent: React.FC<{
  health: HealthResponse | null;
  loading: boolean;
  error: string | null;
}> = ({ health, loading, error }) => {
  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="container">
          <div className="app-header-inner">
            <h1 className="app-title">Isekai: A Life Unwritten</h1>
            <div className="flex items-center gap-4">
              <span className="app-version">v0.1.0</span>
              {health && (
                <span className="badge badge-teal" style={{ textTransform: 'none' }}>
                  {health.service} ({health.status})
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="app-main">
        {/* Connection Failure Alert */}
        {error && (
          <div className="container mt-4">
            <div className="alert alert-error" role="alert">
              <p className="alert-title">Connection Failed</p>
              <p className="alert-message">{error}</p>
              <p className="alert-hint">
                Make sure the backend is running on <code>http://localhost:8000</code>
              </p>
            </div>
          </div>
        )}

        {/* Active Screen */}
        <ScreenRouter />

        {/* System Status & Development Info Section */}
        <section className="container mt-8 mb-8">
          <details
            className="card"
            style={{
              padding: '1rem 1.5rem',
              background: 'var(--color-bg-secondary)',
              border: '1px solid var(--color-border-subtle)',
            }}
          >
            <summary
              className="card-title text-muted"
              style={{ cursor: 'pointer', fontSize: '0.875rem' }}
            >
              System Status &amp; Architecture Details
            </summary>

            <div className="mt-4 card-stack">
              <div className="card-header" style={{ paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>
                <h3 className="card-title" style={{ fontSize: '1rem' }}>
                  System Status
                </h3>
              </div>

              {loading && (
                <div className="loading-box" role="status" aria-live="polite">
                  <div className="spinner" aria-hidden="true" />
                  <span>Checking backend connection...</span>
                </div>
              )}

              {health && (
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

              <div className="card-header mt-4" style={{ paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>
                <h3 className="card-title" style={{ fontSize: '1rem' }}>
                  Development Info
                </h3>
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
          </details>
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
};

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
    <GameProvider>
      <AppContent health={health} loading={loading} error={error} />
    </GameProvider>
  );
}

export default App;
