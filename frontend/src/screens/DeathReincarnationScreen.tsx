/** Death & Reincarnation Screen.
 *
 * Implements SPEC §12.F:
 * - Death narrative & obituary
 * - Life record summary (attributes, skills, days lived, achievements)
 * - Legacy passed down to the next generation
 * - Reincarnation action (into Generation N+1)
 * - Session conclusion option
 */

import React from 'react';
import { useGame } from '../context/GameContext';
import { useLanguage } from '../context/LanguageContext';

export const DeathReincarnationScreen: React.FC = () => {
  const {
    character,
    lifeRecord,
    legacy,
    goToScreen,
    concludeSession,
    loading,
    error,
  } = useGame();
  const { t, language } = useLanguage();

  const charName = lifeRecord?.character_name || character?.name || (language === 'id' ? 'Musafir Fana' : 'Mortal Traveler');
  const generation = lifeRecord?.generation || character?.generation || 1;
  const daysLived = lifeRecord?.days_lived || character?.age || 1;
  const obituary =
    lifeRecord?.obituary ||
    (language === 'id'
      ? 'Gugur di belantara Eldoria yang kejam, hanya menyisakan bisikan di hembusan angin.'
      : 'Fallen in the harsh wilderness of Eldoria, leaving only whispers in the wind.');
  const deathCause = lifeRecord?.death_cause || (language === 'id' ? 'Kelelahan fana' : 'Mortal exhaustion');
  const achievements = lifeRecord?.achievements || [];

  return (
    <div className="container" style={{ maxWidth: '800px', margin: '2rem auto' }}>
      {/* Hero Death Banner */}
      <div className="death-hero mb-6">
        <h1 className="death-title font-display">{t.death.title}</h1>
        <p className="text-secondary" style={{ fontStyle: 'italic', fontSize: '1.125rem' }}>
          {t.common.generation} {generation} &bull; {charName} {t.death.crossed}
        </p>
      </div>

      {error && (
        <div className="alert alert-error mb-4">
          <p className="alert-title">{t.common.error}</p>
          <p className="alert-message">{error}</p>
        </div>
      )}

      {/* Obituary Card */}
      <div className="card mb-6" style={{ borderLeft: '4px solid var(--color-accent-crimson)' }}>
        <div className="card-header flex justify-between items-center">
          <h2 className="card-title text-crimson">{t.death.mortalRecord}</h2>
          <span className="badge badge-crimson">{t.death.cause}: {deathCause}</span>
        </div>

        <p className="text-primary mb-4" style={{ fontSize: '1rem', lineHeight: '1.6' }}>
          "{obituary}"
        </p>

        <div className="flex gap-4 text-muted mb-4" style={{ fontSize: '0.875rem', flexWrap: 'wrap' }}>
          <span>{t.death.daysSurvived}: <strong className="text-primary">{daysLived}</strong></span>
          <span>{t.death.coinsAmassed}: <strong className="text-gold">{lifeRecord?.final_money ?? character?.money ?? 0}g</strong></span>
          <span>{t.death.lineage}: <strong className="text-primary">{lifeRecord?.race || character?.race_name} {lifeRecord?.background || character?.background_name}</strong></span>
        </div>

        {/* Dynamic Achievements */}
        {achievements.length > 0 && (
          <div className="mt-4 pt-3" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
            <h4 className="font-display text-gold mb-2" style={{ fontSize: '0.875rem' }}>
              {t.death.achievementsEarned}:
            </h4>
            <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
              {achievements.map((ach, idx) => (
                <span key={idx} className="badge badge-gold">
                  🏆 {ach}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Legacy Passed to Next Generation */}
      {legacy && (
        <div className="card mb-6" style={{ borderLeft: '4px solid var(--color-accent-gold)' }}>
          <div className="card-header">
            <h2 className="card-title text-gold">{t.death.legacyPassed}</h2>
          </div>
          <p className="text-secondary mb-3" style={{ fontStyle: 'italic', fontSize: '0.9375rem' }}>
            "{legacy.personality_memory || (language === 'id' ? 'Sebagian dari jiwamu mengkristal menjadi berkah leluhur.' : 'A fragment of your spirit crystallizes into an ancestral blessing.')}"
          </p>

          <div className="flex gap-3" style={{ flexWrap: 'wrap' }}>
            {legacy.bonus_attribute && (
              <span className="badge badge-gold" style={{ fontSize: '0.875rem' }}>
                +{legacy.bonus_attribute_value} {legacy.bonus_attribute.toUpperCase()} {language === 'id' ? 'untuk Generasi Berikutnya' : 'for Next Generation'}
              </span>
            )}
            {legacy.skill_affinity && (
              <span className="badge badge-teal" style={{ fontSize: '0.875rem' }}>
                +{legacy.skill_affinity_bonus} {legacy.skill_affinity.toUpperCase()} {language === 'id' ? 'Afinitas Generasi Berikutnya' : 'Affinity for Next Generation'}
              </span>
            )}
            {legacy.money_bonus > 0 && (
              <span className="badge badge-gold" style={{ fontSize: '0.875rem' }}>
                +{legacy.money_bonus} {language === 'id' ? 'Emas Warisan' : 'Inheritance Gold'}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="card flex justify-between items-center" style={{ padding: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <button
          className="btn"
          style={{
            background: 'var(--color-bg-tertiary)',
            color: 'var(--color-text-secondary)',
            border: '1px solid var(--color-border-medium)',
          }}
          onClick={concludeSession}
          disabled={loading}
        >
          📜 {t.death.concludeJourney}
        </button>

        <button
          className="btn btn-primary"
          style={{ padding: '0.875rem 2rem', fontSize: '1.125rem' }}
          onClick={() => goToScreen('character_creation')}
          disabled={loading}
        >
          ✨ {t.death.reincarnate} {generation + 1}
        </button>
      </div>
    </div>
  );
};
