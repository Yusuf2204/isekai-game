/** Session History Screen.
 *
 * Implements SPEC §12.A & §10:
 * - Lists historical sessions
 * - Displays character rosters and completion state
 * - Allows continuing past active sessions
 */

import React, { useEffect, useState } from 'react';
import { useGame } from '../context/GameContext';
import { apiClient } from '../api/client';
import type { SessionHistoryItem } from '../types/game';

export const SessionHistoryScreen: React.FC = () => {
  const { continueGame, goToScreen, loading: contextLoading } = useGame();
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
        if (isMounted) setError(err.message || 'Failed to retrieve chronicles');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="container" style={{ maxWidth: '800px', margin: '2rem auto' }}>
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="font-display text-gold" style={{ fontSize: '2rem' }}>
            Archived Chronicles
          </h1>
          <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
            Past epochs and soul journeys recorded across Eldoria.
          </p>
        </div>

        <button className="btn" style={{ background: 'var(--color-bg-tertiary)' }} onClick={() => goToScreen('main_menu')}>
          ← Return to Menu
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
          <span>Consulting ancient archives...</span>
        </div>
      ) : sessions.length === 0 ? (
        <div className="card text-center text-muted" style={{ padding: '3rem' }}>
          <p>No past chronicles found. A fresh destiny awaits your first soul.</p>
          <button className="btn btn-primary mt-4" onClick={() => goToScreen('character_creation')}>
            Begin First Journey
          </button>
        </div>
      ) : (
        <div className="card-stack">
          {sessions.map((sess) => (
            <div key={sess.id} className="card">
              <div className="flex justify-between items-start mb-2 flex-wrap gap-2">
                <div>
                  <h3 className="font-display text-primary" style={{ fontSize: '1.125rem' }}>
                    Session #{sess.id} &bull; {sess.total_characters} Generation(s)
                  </h3>
                  <p className="text-muted" style={{ fontSize: '0.8125rem' }}>
                    Recorded: {new Date(sess.created_at).toLocaleDateString()}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`badge ${sess.is_active ? 'badge-teal' : 'badge-gold'}`}>
                    {sess.is_active ? 'In Progress' : 'Concluded'}
                  </span>
                  {sess.is_active && (
                    <button
                      className="btn btn-primary"
                      style={{ fontSize: '0.75rem', padding: '0.375rem 0.75rem' }}
                      onClick={() => continueGame(sess.session_token)}
                      disabled={contextLoading}
                    >
                      Resume Life
                    </button>
                  )}
                </div>
              </div>

              {sess.character_names && sess.character_names.length > 0 && (
                <div className="mt-2 text-secondary" style={{ fontSize: '0.875rem' }}>
                  <strong>Soul Vessels: </strong> {sess.character_names.join(' → ')}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
