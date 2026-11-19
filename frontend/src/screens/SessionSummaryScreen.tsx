/** Session Summary Screen.
 *
 * Implements SPEC §12.G:
 * - Multi-generation lineage summary
 * - Important events & lifetime milestones
 * - Generational legacy and achievements
 * - Return to Main Menu or start fresh session
 */

import React, { useEffect, useState } from 'react';
import { useGame } from '../context/GameContext';
import { apiClient } from '../api/client';
import type { SessionSummaryResponse } from '../types/game';

export const SessionSummaryScreen: React.FC = () => {
  const { sessionToken, sessionSummary, startNewGame, resetToMainMenu } = useGame();
  const [localSummary, setLocalSummary] = useState<SessionSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const summary = sessionSummary || localSummary;

  useEffect(() => {
    let isMounted = true;
    if (sessionToken && !sessionSummary && !localSummary) {
      setLoading(true);
      apiClient
        .getSessionSummary(sessionToken)
        .then((resp) => {
          if (isMounted) setLocalSummary(resp);
        })
        .catch(() => {})
        .finally(() => {
          if (isMounted) setLoading(false);
        });
    }
    return () => {
      isMounted = false;
    };
  }, [sessionToken, sessionSummary, localSummary]);

  if (loading) {
    return (
      <div className="container text-center" style={{ margin: '4rem auto' }}>
        <div className="spinner" style={{ margin: '0 auto 1rem auto' }} />
        <p className="text-secondary">Compiling genealogical chronicles...</p>
      </div>
    );
  }

  return (
    <div className="container" style={{ maxWidth: '900px', margin: '2rem auto' }}>
      <div className="mb-6 text-center">
        <h1 className="font-display text-gold" style={{ fontSize: '2.25rem' }}>
          CHRONICLES OF THE TRANSMIGRATED SOUL
        </h1>
        <p className="text-secondary" style={{ fontStyle: 'italic' }}>
          The complete generational tapestry woven by your soul in Eldoria.
        </p>
      </div>

      {summary && (
        <>
          {/* Aggregate Metrics */}
          <div className="card mb-6" style={{ background: 'var(--color-bg-secondary)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', textAlign: 'center' }}>
              <div>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>TOTAL GENERATIONS</div>
                <div className="text-gold font-bold font-display" style={{ fontSize: '2rem' }}>
                  {summary.total_characters}
                </div>
              </div>
              <div>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>TOTAL DAYS LIVED</div>
                <div className="text-primary font-bold font-display" style={{ fontSize: '2rem' }}>
                  {summary.total_days_lived}
                </div>
              </div>
              <div>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>ACHIEVEMENTS EARNED</div>
                <div className="text-teal font-bold font-display" style={{ fontSize: '2rem' }}>
                  {summary.total_achievements}
                </div>
              </div>
              <div>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>SESSION STATUS</div>
                <div className="font-bold font-display" style={{ fontSize: '1.25rem', color: summary.is_active ? 'var(--color-success)' : 'var(--color-text-muted)', marginTop: '0.375rem' }}>
                  {summary.is_active ? 'ACTIVE' : 'CONCLUDED'}
                </div>
              </div>
            </div>
          </div>

          {/* Chronological Roster of Generations */}
          <h2 className="font-display text-primary mb-4" style={{ fontSize: '1.5rem' }}>
            Generational Lineage
          </h2>

          <div className="card-stack mb-8">
            {(summary.characters_created || summary.characters || []).map((char) => (
              <div
                key={char.id || char.character_id}
                className="card"
                style={{
                  borderLeft: `4px solid ${char.is_alive ? 'var(--color-success)' : 'var(--color-accent-gold)'}`,
                }}
              >
                <div className="flex justify-between items-start mb-2 flex-wrap gap-2">
                  <div>
                    <div className="flex items-center gap-3">
                      <h3 className="font-display text-gold" style={{ fontSize: '1.25rem' }}>
                        Gen {char.generation}: {char.name}
                      </h3>
                      <span className="badge badge-gold">{char.race_name}</span>
                      <span className="badge">{char.background_name}</span>
                    </div>
                    <div className="text-muted" style={{ fontSize: '0.8125rem', marginTop: '0.25rem' }}>
                      Survived: <strong>{char.days_lived || char.age || 0} days</strong> &bull; Wealth: <strong>{char.money || 0} gold</strong>
                    </div>
                  </div>

                  <span className={`badge ${char.is_alive ? 'badge-teal' : 'badge-crimson'}`}>
                    {char.is_alive ? 'Living' : char.death_cause || char.cause_of_death ? `Fallen (${char.death_cause || char.cause_of_death})` : 'Retired'}
                  </span>
                </div>

                {(char.obituary || char.death_description) && (
                  <p className="text-secondary mt-2 mb-3" style={{ fontStyle: 'italic', fontSize: '0.875rem' }}>
                    "{char.obituary || char.death_description}"
                  </p>
                )}

                {/* Legacy passed */}
                {char.legacy_left && (
                  <div className="mt-3 pt-2" style={{ borderTop: '1px solid var(--color-border-subtle)', fontSize: '0.8125rem' }}>
                    <span className="text-muted">Legacy passed to descendants: </span>
                    {char.legacy_left.bonus_attribute && (
                      <span className="badge badge-gold" style={{ marginLeft: '0.5rem' }}>
                        +{char.legacy_left.bonus_attribute_value} {char.legacy_left.bonus_attribute.toUpperCase()}
                      </span>
                    )}
                    {char.legacy_left.skill_affinity && (
                      <span className="badge badge-teal" style={{ marginLeft: '0.5rem' }}>
                        +{char.legacy_left.skill_affinity_bonus} {char.legacy_left.skill_affinity.toUpperCase()}
                      </span>
                    )}
                  </div>
                )}

                {/* Achievements */}
                {Array.isArray(char.achievements) && char.achievements.length > 0 && (
                  <div className="flex gap-2 mt-3 flex-wrap">
                    {char.achievements.map((ach, idx) => (
                      <span key={idx} className="badge badge-gold">
                        🏆 {ach}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {/* Footer Navigation */}
      <div className="flex justify-between items-center flex-wrap gap-4">
        <button className="btn" style={{ background: 'var(--color-bg-tertiary)' }} onClick={resetToMainMenu}>
          ← Return to Main Menu
        </button>

        <button className="btn btn-primary" onClick={startNewGame}>
          ✨ Begin a Brand New Journey
        </button>
      </div>
    </div>
  );
};
