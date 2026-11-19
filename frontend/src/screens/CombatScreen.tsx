/** Combat Screen.
 *
 * Implements SPEC §12.E:
 * - Player status panel (HP, Stamina)
 * - Enemy status panel (HP, Type, Stats)
 * - Turn-based Combat log
 * - 5 turn actions: Attack, Defend, Use Skill, Use Item, Flee
 * - Victory resolution & defeat handling
 */

import React from 'react';
import { useGame } from '../context/GameContext';
import { useLanguage } from '../context/LanguageContext';

export const CombatScreen: React.FC = () => {
  const {
    combatState,
    executeCombatAction,
    goToScreen,
    refreshAuthoritativeState,
    loading,
    error,
  } = useGame();
  const { t, language } = useLanguage();

  if (!combatState) {
    return (
      <div className="container text-center" style={{ margin: '4rem auto' }}>
        <p className="text-muted">{t.combat.noBattle}</p>
        <button className="btn btn-primary mt-4" onClick={() => goToScreen('gameplay')}>
          {t.combat.returnExploration}
        </button>
      </div>
    );
  }

  const { enemy, player, combat_log, status, rewards } = combatState;

  const enemyHpPercent = Math.min(100, Math.max(0, (enemy.current_health / enemy.max_health) * 100));
  const playerHpPercent = Math.min(100, Math.max(0, (player.current_health / player.max_health) * 100));
  const playerStaminaPercent = Math.min(100, Math.max(0, (player.current_stamina / player.max_stamina) * 100));

  const handleReturnToGameplay = async () => {
    await refreshAuthoritativeState();
    goToScreen('gameplay');
  };

  return (
    <div className="container combat-container" style={{ margin: '2rem auto' }}>
      <div className="mb-6 text-center">
        <span className="badge badge-crimson" style={{ fontSize: '0.875rem' }}>
          ⚔️ {t.combat.title} &bull; {t.common.turn} {combatState.turn}
        </span>
        <h1 className="font-display text-gold mt-2" style={{ fontSize: '2rem' }}>
          {language === 'id' ? 'Pertarungan' : 'Encounter'}: {enemy.name}
        </h1>
        <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
          {enemy.description}
        </p>
      </div>

      {error && (
        <div className="alert alert-error mb-4">
          <p className="alert-title">{t.common.error}</p>
          <p className="alert-message">{error}</p>
        </div>
      )}

      {/* Combat Arena: Enemy & Player Cards */}
      <div className="combat-arena">
        {/* Enemy Card */}
        <div className="combat-card combat-card-enemy">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-display text-crimson" style={{ fontSize: '1.25rem' }}>
              {enemy.name}
            </h3>
            <span className="badge badge-crimson">{t.common.level} {enemy.level}</span>
          </div>

          <div className="mb-3">
            <div className="flex justify-between text-muted mb-1" style={{ fontSize: '0.8125rem' }}>
              <span>{t.combat.hp}</span>
              <span>
                {enemy.current_health} / {enemy.max_health}
              </span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-bar-fill progress-bar-health"
                style={{ width: `${enemyHpPercent}%` }}
              />
            </div>
          </div>

          <div className="flex justify-between text-muted" style={{ fontSize: '0.75rem' }}>
            <span>ATK: {enemy.attack_power}</span>
            <span>DEF: {enemy.defense}</span>
            <span>AGI: {enemy.agility}</span>
          </div>
        </div>

        {/* Player Card */}
        <div className="combat-card combat-card-player">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-display text-gold" style={{ fontSize: '1.25rem' }}>
              {language === 'id' ? 'Kamu (Wadah Fana)' : 'You (Mortal Vessel)'}
            </h3>
            <span className="badge badge-teal">{t.common.level} {player.level}</span>
          </div>

          <div className="mb-3">
            <div className="flex justify-between text-muted mb-1" style={{ fontSize: '0.8125rem' }}>
              <span>{t.combat.hp}</span>
              <span>
                {player.current_health} / {player.max_health}
              </span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-bar-fill progress-bar-health"
                style={{ width: `${playerHpPercent}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-muted mb-1" style={{ fontSize: '0.8125rem' }}>
              <span>Stamina (STA)</span>
              <span>
                {player.current_stamina} / {player.max_stamina}
              </span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-bar-fill progress-bar-stamina"
                style={{ width: `${playerStaminaPercent}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Combat Log */}
      <div className="card mb-6">
        <h4 className="font-display text-muted mb-2" style={{ fontSize: '0.875rem' }}>
          {t.combat.combatChronicle}
        </h4>
        <div className="combat-log-box">
          {(combat_log || []).map((log, index) => (
            <div key={index} style={{ color: log.includes('defeats') || log.includes('CRITICAL') ? 'var(--color-accent-gold-light)' : 'var(--color-text-secondary)' }}>
              &gt; {log}
            </div>
          ))}
        </div>
      </div>

      {/* Outcome Cards or Action Buttons */}
      {status === 'victory' && (
        <div className="alert mb-6" style={{ background: 'rgba(74, 139, 92, 0.2)', border: '1px solid var(--color-success)', textAlign: 'center', padding: '1.5rem' }}>
          <h2 className="font-display" style={{ color: 'var(--color-success)', fontSize: '1.75rem', marginBottom: '0.5rem' }}>
            {t.combat.victory}
          </h2>
          <p className="text-secondary mb-4">{t.combat.victorySubtitle}</p>
          {rewards && (
            <div className="flex justify-center gap-4 mb-4" style={{ flexWrap: 'wrap' }}>
              <span className="badge badge-gold">+{rewards.character_xp || 0} {t.common.xp}</span>
              <span className="badge badge-gold">+{rewards.money || 0} {t.common.gold}</span>
              {Array.isArray(rewards.loot) && rewards.loot.map((it) => (
                <span key={it.item_id || it.name} className="badge badge-teal">
                  {language === 'id' ? 'Didapat' : 'Looted'}: {it.name}
                </span>
              ))}
              {Array.isArray(rewards.loot_gained) && rewards.loot_gained.map((itName, idx) => (
                <span key={idx} className="badge badge-teal">
                  {language === 'id' ? 'Didapat' : 'Looted'}: {itName}
                </span>
              ))}
            </div>
          )}
          <button className="btn btn-primary" onClick={handleReturnToGameplay}>
            {t.combat.claimVictory}
          </button>
        </div>
      )}

      {status === 'fled' && (
        <div className="alert mb-6" style={{ background: 'rgba(61, 139, 139, 0.2)', border: '1px solid var(--color-accent-teal)', textAlign: 'center', padding: '1.5rem' }}>
          <h2 className="font-display text-teal" style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>
            {t.combat.fled}
          </h2>
          <p className="text-secondary mb-4">{t.combat.fledSubtitle}</p>
          <button className="btn btn-primary" onClick={handleReturnToGameplay}>
            {t.combat.returnExploration}
          </button>
        </div>
      )}

      {status === 'active' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">{language === 'id' ? 'Pilih Tindakan Giliran' : 'Choose Turn Action'}</h3>
          </div>
          <div className="combat-actions-bar">
            <button
              className="btn btn-primary"
              style={{ flex: 1, minWidth: '130px', padding: '0.875rem' }}
              onClick={() => executeCombatAction('attack')}
              disabled={loading || player.current_stamina < 10}
            >
              {t.combat.attack}
            </button>

            <button
              className="btn"
              style={{
                flex: 1,
                minWidth: '130px',
                padding: '0.875rem',
                background: 'var(--color-bg-tertiary)',
                color: 'var(--color-text-primary)',
                border: '1px solid var(--color-border-medium)',
              }}
              onClick={() => executeCombatAction('defend')}
              disabled={loading}
            >
              {t.combat.defend}
            </button>

            <button
              className="btn"
              style={{
                flex: 1,
                minWidth: '130px',
                padding: '0.875rem',
                background: 'var(--color-bg-elevated)',
                color: 'var(--color-accent-gold)',
                border: '1px solid var(--color-accent-gold-dark)',
              }}
              onClick={() => executeCombatAction('use_skill')}
              disabled={loading || player.current_stamina < 15}
            >
              {t.combat.useSkill}
            </button>

            <button
              className="btn"
              style={{
                flex: 1,
                minWidth: '130px',
                padding: '0.875rem',
                background: 'var(--color-bg-tertiary)',
                color: 'var(--color-accent-teal)',
                border: '1px solid var(--color-accent-teal)',
              }}
              onClick={() => executeCombatAction('use_item')}
              disabled={loading}
            >
              {t.combat.useItem}
            </button>

            <button
              className="btn"
              style={{
                flex: 1,
                minWidth: '130px',
                padding: '0.875rem',
                background: 'var(--color-bg-tertiary)',
                color: 'var(--color-text-secondary)',
                border: '1px solid var(--color-border-subtle)',
              }}
              onClick={() => executeCombatAction('flee')}
              disabled={loading}
            >
              {t.combat.flee}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
