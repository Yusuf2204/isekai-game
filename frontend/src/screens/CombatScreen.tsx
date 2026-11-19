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

export const CombatScreen: React.FC = () => {
  const {
    combatState,
    executeCombatAction,
    goToScreen,
    refreshAuthoritativeState,
    loading,
    error,
  } = useGame();

  if (!combatState) {
    return (
      <div className="container text-center" style={{ margin: '4rem auto' }}>
        <p className="text-muted">No battle currently engaged.</p>
        <button className="btn btn-primary mt-4" onClick={() => goToScreen('gameplay')}>
          Return to Exploration
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
          ⚔️ Turn-Based Combat &bull; Turn {combatState.turn}
        </span>
        <h1 className="font-display text-gold mt-2" style={{ fontSize: '2rem' }}>
          Encounter: {enemy.name}
        </h1>
        <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
          {enemy.description}
        </p>
      </div>

      {error && (
        <div className="alert alert-error mb-4">
          <p className="alert-title">Combat Error</p>
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
            <span className="badge badge-crimson">Lv. {enemy.level}</span>
          </div>

          <div className="mb-3">
            <div className="flex justify-between text-muted mb-1" style={{ fontSize: '0.8125rem' }}>
              <span>Health (HP)</span>
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
              You (Mortal Vessel)
            </h3>
            <span className="badge badge-teal">Lv. {player.level}</span>
          </div>

          <div className="mb-3">
            <div className="flex justify-between text-muted mb-1" style={{ fontSize: '0.8125rem' }}>
              <span>Vitality (HP)</span>
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
          Combat Chronicle
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
            Victory Achieved!
          </h2>
          <p className="text-secondary mb-4">The beast has fallen before your blade and resolve.</p>
          {rewards && (
            <div className="flex justify-center gap-4 mb-4" style={{ flexWrap: 'wrap' }}>
              <span className="badge badge-gold">+{rewards.character_xp || 0} Character XP</span>
              <span className="badge badge-gold">+{rewards.money || 0} Gold Coins</span>
              {Array.isArray(rewards.loot) && rewards.loot.map((it) => (
                <span key={it.item_id || it.name} className="badge badge-teal">
                  Looted: {it.name}
                </span>
              ))}
              {Array.isArray(rewards.loot_gained) && rewards.loot_gained.map((itName, idx) => (
                <span key={idx} className="badge badge-teal">
                  Looted: {itName}
                </span>
              ))}
            </div>
          )}
          <button className="btn btn-primary" onClick={handleReturnToGameplay}>
            Claim Victory & Continue Journey
          </button>
        </div>
      )}

      {status === 'fled' && (
        <div className="alert mb-6" style={{ background: 'rgba(61, 139, 139, 0.2)', border: '1px solid var(--color-accent-teal)', textAlign: 'center', padding: '1.5rem' }}>
          <h2 className="font-display text-teal" style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>
            Tactical Retreat Successful
          </h2>
          <p className="text-secondary mb-4">You evaded the enemy's grasp into the shadows.</p>
          <button className="btn btn-primary" onClick={handleReturnToGameplay}>
            Return to Safety
          </button>
        </div>
      )}

      {status === 'active' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Choose Turn Action</h3>
          </div>
          <div className="combat-actions-bar">
            <button
              className="btn btn-primary"
              style={{ flex: 1, minWidth: '130px', padding: '0.875rem' }}
              onClick={() => executeCombatAction('attack')}
              disabled={loading || player.current_stamina < 10}
            >
              ⚔️ Attack (-10 STA)
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
              🛡️ Defend (+5 STA, -50% DMG)
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
              ⚡ Strike Skill (-15 STA)
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
              🧪 Use Potion
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
              🏃 Flee Battle
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
