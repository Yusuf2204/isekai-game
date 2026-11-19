/** Session History Screen.
 *
 * Implements SPEC §12.A & §10:
 * - Lists historical sessions
 * - Displays character rosters and completion state
 * - Allows continuing past active sessions
 */

import React, { useEffect, useState } from 'react';
import { useGame } from '../context/GameContext';
import { useLanguage } from '../context/LanguageContext';
import { apiClient } from '../api/client';
import type { SessionHistoryItem } from '../types/game';

export const SessionHistoryScreen: React.FC = () => {
  const { continueGame, goToScreen, loading: contextLoading } = useGame();
  const { t, language } = useLanguage();
  const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    apiClient
      .getSessionHistory()
      .then((resp) => {
        if (isMounted) setSessions(resp.sessions);
      })
      .catch((err) => {
        if (isMounted) setError(err.message || (language === 'id' ? 'Gagal mengambil arsip kronik' : 'Failed to retrieve chronicles'));
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [language]);

  return (
    <div className="container" style={{ maxWidth: '800px', margin: '2rem auto' }}>
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="font-display text-gold" style={{ fontSize: '2rem' }}>
            {t.history.title}
          </h1>
          <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
            {t.history.subtitle}
          </p>
        </div>

        <button className="btn" style={{ background: 'var(--color-bg-tertiary)' }} onClick={() => goToScreen('main_menu')}>
          ← {t.history.returnMenu}
        </button>
      </div>

      {error && (
        <div className="alert alert-error mb-4">
          <p className="alert-message">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="card text-center text-muted" style={{ padding: '3rem' }}>
          <div className="spinner" style={{ margin: '0 auto 1rem auto' }} />
          <span>{language === 'id' ? 'Membuka arsip kuno...' : 'Consulting ancient archives...'}</span>
        </div>
      ) : sessions.length === 0 ? (
        <div className="card text-center text-muted" style={{ padding: '3rem' }}>
          <p>{t.history.noChronicles}</p>
          <button className="btn btn-primary mt-4" onClick={() => goToScreen('character_creation')}>
            {t.history.beginFirst}
          </button>
        </div>
      ) : (
        <div className="card-stack">
          {sessions.map((sess) => (
            <div key={sess.id} className="card">
              <div className="flex justify-between items-start mb-2 flex-wrap gap-2">
                <div>
                  <h3 className="font-display text-primary" style={{ fontSize: '1.125rem' }}>
                    {t.history.sessionNumber} #{sess.id} &bull; {sess.total_characters} {t.history.generationsCount}
                  </h3>
                  <p className="text-muted" style={{ fontSize: '0.8125rem' }}>
                    {t.history.recordedDate}: {new Date(sess.created_at).toLocaleDateString(language === 'id' ? 'id-ID' : 'en-US')}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`badge ${sess.is_active ? 'badge-teal' : 'badge-gold'}`}>
                    {sess.is_active ? t.history.inProgress : t.history.concluded}
                  </span>
                  {sess.is_active && (
                    <button
                      className="btn btn-primary"
                      style={{ fontSize: '0.75rem', padding: '0.375rem 0.75rem' }}
                      onClick={() => continueGame(sess.session_token)}
                      disabled={contextLoading}
                    >
                      {t.history.resume}
                    </button>
                  )}
                </div>
              </div>

              {sess.character_names && sess.character_names.length > 0 && (
                <div className="mt-2 text-secondary" style={{ fontSize: '0.875rem' }}>
                  <strong>{language === 'id' ? 'Wadah Jiwa: ' : 'Soul Vessels: '}</strong> {sess.character_names.join(' → ')}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
