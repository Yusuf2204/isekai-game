/** Main Menu Screen.
 *
 * Implements SPEC §12.A:
 * - New Game
 * - Continue Game
 * - Session History
 */

import React, { useEffect, useState } from 'react';
import { useGame } from '../context/GameContext';
import { useLanguage } from '../context/LanguageContext';
import { apiClient } from '../api/client';
import type { HealthResponse } from '../types/api';

export const MainMenuScreen: React.FC = () => {
  const { sessionToken, startNewGame, continueGame, goToScreen, loading, error } = useGame();
  const { t } = useLanguage();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let isMounted = true;
    apiClient
      .healthCheck()
      .then((h) => {
        if (isMounted) setHealth(h);
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="container" style={{ maxWidth: '640px', margin: '4rem auto', textAlign: 'center' }}>
      <div className="mb-8">
        <h1 className="text-gold font-display" style={{ fontSize: '3rem', letterSpacing: '0.08em', marginBottom: '0.5rem' }}>
          {t.common.title}
        </h1>
        <p className="text-secondary" style={{ fontStyle: 'italic', fontSize: '1.125rem' }}>
          {t.mainMenu.tagline}
        </p>
      </div>

      {error && (
        <div className="alert alert-error text-left mb-6">
          <p className="alert-title">{t.common.error}</p>
          <p className="alert-message">{error}</p>
        </div>
      )}

      <div className="card card-stack" style={{ padding: '2rem' }}>
        <button
          className="btn btn-primary"
          style={{ width: '100%', padding: '1rem', fontSize: '1.125rem' }}
          onClick={startNewGame}
          disabled={loading}
        >
          {loading ? t.mainMenu.communing : t.mainMenu.beginNew}
        </button>

        <button
          className="btn"
          style={{
            width: '100%',
            padding: '1rem',
            background: 'var(--color-bg-tertiary)',
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-border-medium)',
          }}
          onClick={() => continueGame()}
          disabled={!sessionToken || loading}
          title={!sessionToken ? 'No saved active session found' : 'Resume active session'}
        >
          {sessionToken ? t.mainMenu.continueSaved : t.mainMenu.noSaved}
        </button>

        <button
          className="btn"
          style={{
            width: '100%',
            padding: '0.875rem',
            background: 'transparent',
            color: 'var(--color-text-secondary)',
            border: '1px solid var(--color-border-subtle)',
          }}
          onClick={() => goToScreen('history')}
          disabled={loading}
        >
          {t.mainMenu.chronicles}
        </button>
      </div>

      <div className="mt-8 text-muted" style={{ fontSize: '0.875rem' }}>
        {health ? (
          <span>
            {t.mainMenu.realmConnection}: <strong className="text-gold">{health.service}</strong> ({health.status})
          </span>
        ) : (
          <span>{t.mainMenu.connecting}</span>
        )}
      </div>
    </div>
  );
};
