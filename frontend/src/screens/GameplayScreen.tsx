/** Main Gameplay Screen.
 *
 * Implements SPEC §12.C (Main Gameplay) & §12.D (Character Profile):
 * - Character status header (health, stamina, fatigue, gold, time)
 * - Location narrative banner
 * - Tabbed panels: Activities, World/Travel, Profile, NPCs, Conditions
 * - Authoritative backend interaction
 * - Event Modal overlay
 */

import React, { useEffect, useState } from 'react';
import { useGame } from '../context/GameContext';
import { apiClient } from '../api/client';
import type { NPCSummary, LocationSummary } from '../types/game';

export const GameplayScreen: React.FC = () => {
  const {
    sessionToken,
    character,
    resources,
    timeState,
    currentLocation,
    locations,
    activeTab,
    setActiveTab,
    narrativeLogs,
    activeEvent,
    performExplore,
    performRest,
    performWork,
    travelToLocation,
    advanceTime,
    allocateAttributePoint,
    useInventoryItem,
    treatCondition,
    inspectConditionTreatments,
    availableTreatments,
    conditions,
    triggerRandomEvent,
    resolveEventChoice,
    startCombatEncounter,
    interactWithNpc,
    giftNpc,
    npcDialogue,
    concludeSession,
    loading,
    error,
  } = useGame();

  const [locationNpcs, setLocationNpcs] = useState<NPCSummary[]>([]);
  const giftGoldAmount = 10;

  // Load NPCs at current location when location changes
  useEffect(() => {
    let isMounted = true;
    if (sessionToken && currentLocation?.location?.id) {
      apiClient
        .getNPCsAtLocation(currentLocation.location.id, sessionToken)
        .then((resp) => {
          if (isMounted) setLocationNpcs(resp.npcs);
        })
        .catch(() => {});
    }
    return () => {
      isMounted = false;
    };
  }, [sessionToken, currentLocation?.location?.id]);

  if (!character) {
    return (
      <div className="container text-center" style={{ margin: '4rem auto' }}>
        <div className="spinner" style={{ margin: '0 auto 1rem auto' }} />
        <p className="text-secondary">Attuning to mortal vessel...</p>
      </div>
    );
  }

  const currentHp = resources?.health.current ?? character.current_health;
  const maxHp = resources?.health.max ?? character.max_health;
  const hpPercent = Math.min(100, Math.max(0, (currentHp / maxHp) * 100));

  const currentStamina = resources?.stamina.current ?? 100;
  const maxStamina = resources?.stamina.effective_max ?? resources?.stamina.max ?? 100;
  const staminaPercent = Math.min(100, Math.max(0, (currentStamina / maxStamina) * 100));

  const fatigueLevel = resources?.fatigue.level ?? 0;
  const currentMoney = resources?.money ?? character.money;

  return (
    <div className="container" style={{ maxWidth: '1100px', margin: '1.5rem auto' }}>
      {/* --- Character Status Header --- */}
      <header className="char-header">
        <div className="char-title-row">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-display text-gold" style={{ fontSize: '1.75rem' }}>
                {character.name}
              </h1>
              <span className="badge badge-gold">Gen {character.generation}</span>
              <span className="badge badge-teal">{character.race_name}</span>
              <span className="badge">{character.background_name}</span>
            </div>
            <p className="text-muted" style={{ fontSize: '0.875rem', marginTop: '0.25rem' }}>
              Age {character.age} &bull; Personality: <em>{character.personality_trait}</em>
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-gold font-bold" style={{ fontSize: '1.25rem' }}>
                💰 {currentMoney} Coins
              </div>
              <div className="text-muted" style={{ fontSize: '0.8125rem' }}>
                Day {timeState?.current_day ?? 1} &bull; {timeState?.current_time_of_day ?? 'morning'}
              </div>
            </div>
            <button
              className="btn"
              style={{
                fontSize: '0.8125rem',
                padding: '0.5rem 0.75rem',
                background: 'var(--color-bg-tertiary)',
                color: 'var(--color-text-secondary)',
                border: '1px solid var(--color-border-medium)',
              }}
              onClick={() => advanceTime(1)}
              disabled={loading}
              title="Wait for time to pass (1 period)"
            >
              ⏳ Wait
            </button>
            <button
              className="btn btn-outline"
              style={{
                fontSize: '0.8125rem',
                padding: '0.5rem 0.75rem',
                color: 'var(--color-accent-crimson-light)',
                borderColor: 'var(--color-accent-crimson-dark)',
              }}
              onClick={concludeSession}
              disabled={loading}
              title="Gracefully retire and view multi-generation chronicles"
            >
              📜 Conclude Epoch
            </button>
          </div>
        </div>

        {/* Resource Gauges */}
        <div className="resource-gauges">
          <div className="resource-gauge">
            <div className="flex justify-between items-center mb-1">
              <span className="text-muted font-bold" style={{ fontSize: '0.75rem' }}>
                VITALITY (HP)
              </span>
              <span className="text-primary font-bold" style={{ fontSize: '0.875rem' }}>
                {currentHp} / {maxHp}
              </span>
            </div>
            <div className="progress-bar">
              <div className="progress-bar-fill progress-bar-health" style={{ width: `${hpPercent}%` }} />
            </div>
          </div>

          <div className="resource-gauge">
            <div className="flex justify-between items-center mb-1">
              <span className="text-muted font-bold" style={{ fontSize: '0.75rem' }}>
                STAMINA (STA)
              </span>
              <span className="text-primary font-bold" style={{ fontSize: '0.875rem' }}>
                {currentStamina} / {maxStamina}
              </span>
            </div>
            <div className="progress-bar">
              <div className="progress-bar-fill progress-bar-stamina" style={{ width: `${staminaPercent}%` }} />
            </div>
          </div>

          <div className="resource-gauge">
            <div className="flex justify-between items-center mb-1">
              <span className="text-muted font-bold" style={{ fontSize: '0.75rem' }}>
                FATIGUE
              </span>
              <span className="text-primary font-bold" style={{ fontSize: '0.875rem' }}>
                {fatigueLevel} / 100
              </span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${fatigueLevel}%`,
                  background: fatigueLevel > 50 ? 'var(--color-accent-crimson)' : 'var(--color-accent-gold)',
                }}
              />
            </div>
          </div>
        </div>
      </header>

      {error && (
        <div className="alert alert-error mb-4">
          <p className="alert-title">Notice</p>
          <p className="alert-message">{error}</p>
        </div>
      )}

      {/* --- Main Gameplay Layout --- */}
      <div className="gameplay-layout">
        {/* Left Area: Tabbed Content */}
        <div>
          {/* Tabs */}
          <nav className="nav-tabs">
            <button
              className={`nav-tab ${activeTab === 'activities' ? 'nav-tab-active' : ''}`}
              onClick={() => setActiveTab('activities')}
            >
              Activities
            </button>
            <button
              className={`nav-tab ${activeTab === 'world' ? 'nav-tab-active' : ''}`}
              onClick={() => setActiveTab('world')}
            >
              World & Travel
            </button>
            <button
              className={`nav-tab ${activeTab === 'profile' ? 'nav-tab-active' : ''}`}
              onClick={() => setActiveTab('profile')}
            >
              Profile & Attributes {character.attribute_points > 0 && `(+${character.attribute_points})`}
            </button>
            <button
              className={`nav-tab ${activeTab === 'npcs' ? 'nav-tab-active' : ''}`}
              onClick={() => setActiveTab('npcs')}
            >
              NPCs & Society ({locationNpcs.length})
            </button>
            <button
              className={`nav-tab ${activeTab === 'conditions' ? 'nav-tab-active' : ''}`}
              onClick={() => setActiveTab('conditions')}
            >
              Conditions {conditions.length > 0 && `(${conditions.length})`}
            </button>
          </nav>

          {/* Tab 1: Activities */}
          {activeTab === 'activities' && (
            <div>
              <div className="card mb-6" style={{ background: 'var(--color-bg-secondary)' }}>
                <h3 className="font-display text-gold" style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>
                  Current Location: {currentLocation?.location?.name || 'Unknown Sanctuary'}
                </h3>
                <p className="text-secondary" style={{ fontSize: '0.875rem', marginBottom: '1rem' }}>
                  {currentLocation?.location?.description || 'A quiet crossroads in the land of Eldoria.'}
                </p>

                <div className="flex gap-3" style={{ flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-primary"
                    onClick={() => performExplore()}
                    disabled={loading || currentStamina < 15}
                  >
                    🗺️ Explore Surroundings (-15 STA)
                  </button>

                  <button
                    className="btn"
                    style={{
                      background: 'var(--color-bg-tertiary)',
                      color: 'var(--color-text-primary)',
                      border: '1px solid var(--color-border-medium)',
                    }}
                    onClick={() => performRest('short')}
                    disabled={loading}
                  >
                    ☕ Short Rest (+STA)
                  </button>

                  <button
                    className="btn"
                    style={{
                      background: 'var(--color-bg-tertiary)',
                      color: 'var(--color-text-primary)',
                      border: '1px solid var(--color-border-medium)',
                    }}
                    onClick={() => performRest('long')}
                    disabled={loading}
                  >
                    🛌 Long Rest (Full Sleep)
                  </button>

                  <button
                    className="btn"
                    style={{
                      background: 'var(--color-bg-tertiary)',
                      color: 'var(--color-accent-gold)',
                      border: '1px solid var(--color-accent-gold-dark)',
                    }}
                    onClick={() => triggerRandomEvent()}
                    disabled={loading}
                  >
                    ✨ Seek Destiny (Event)
                  </button>

                  <button
                    className="btn"
                    style={{
                      background: 'var(--color-accent-crimson-dark)',
                      color: 'var(--color-accent-crimson-light)',
                      border: '1px solid var(--color-accent-crimson)',
                    }}
                    onClick={() => startCombatEncounter()}
                    disabled={loading}
                  >
                    ⚔️ Confront Danger (Combat)
                  </button>
                </div>
              </div>

              {/* Work Opportunities */}
              <h4 className="font-display text-primary mb-3" style={{ fontSize: '1.125rem' }}>
                Labor & Vocation
              </h4>
              <div className="grid-cards">
                <div className="action-card">
                  <div>
                    <h5 className="font-display text-gold" style={{ fontSize: '1rem' }}>
                      Day Labor
                    </h5>
                    <p className="text-muted" style={{ fontSize: '0.8125rem' }}>
                      Physical hauling and field labor. Builds endurance and earns honest coin.
                    </p>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="badge badge-gold">~8-15 Coins</span>
                    <button
                      className="btn"
                      style={{
                        padding: '0.375rem 0.75rem',
                        fontSize: '0.8125rem',
                        background: 'var(--color-bg-elevated)',
                        color: 'var(--color-text-primary)',
                      }}
                      onClick={() => performWork('day_labor')}
                      disabled={loading || currentStamina < 20}
                    >
                      Work (-20 STA)
                    </button>
                  </div>
                </div>

                <div className="action-card">
                  <div>
                    <h5 className="font-display text-gold" style={{ fontSize: '1rem' }}>
                      Guild Scribe
                    </h5>
                    <p className="text-muted" style={{ fontSize: '0.8125rem' }}>
                      Copying scrolls and ledger accounting. Sharpens intellect and etiquette.
                    </p>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="badge badge-gold">~15-25 Coins</span>
                    <button
                      className="btn"
                      style={{
                        padding: '0.375rem 0.75rem',
                        fontSize: '0.8125rem',
                        background: 'var(--color-bg-elevated)',
                        color: 'var(--color-text-primary)',
                      }}
                      onClick={() => performWork('guild_scribe')}
                      disabled={loading || currentStamina < 15}
                    >
                      Work (-15 STA)
                    </button>
                  </div>
                </div>

                <div className="action-card">
                  <div>
                    <h5 className="font-display text-gold" style={{ fontSize: '1rem' }}>
                      Caravan Guard
                    </h5>
                    <p className="text-muted" style={{ fontSize: '0.8125rem' }}>
                      Patrolling trade caravans against marauders. Advances swordsmanship.
                    </p>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="badge badge-gold">~20-35 Coins</span>
                    <button
                      className="btn"
                      style={{
                        padding: '0.375rem 0.75rem',
                        fontSize: '0.8125rem',
                        background: 'var(--color-bg-elevated)',
                        color: 'var(--color-text-primary)',
                      }}
                      onClick={() => performWork('caravan_guard')}
                      disabled={loading || currentStamina < 25}
                    >
                      Work (-25 STA)
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: World & Travel */}
          {activeTab === 'world' && (
            <div>
              <h3 className="font-display text-gold mb-4" style={{ fontSize: '1.25rem' }}>
                Kingdom of Eldoria — Waypoints & Settlements
              </h3>
              <div className="grid-cards">
                {locations.map((loc: LocationSummary) => {
                  const isCurrent = currentLocation?.location?.id === loc.id;
                  return (
                    <div
                      key={loc.id}
                      className="action-card"
                      style={{
                        borderColor: isCurrent ? 'var(--color-accent-gold)' : undefined,
                        background: isCurrent ? 'var(--color-bg-elevated)' : undefined,
                      }}
                    >
                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <h4 className="font-display text-primary" style={{ fontSize: '1.05rem' }}>
                            {loc.name}
                          </h4>
                          <span className={`badge ${loc.danger_level > 2 ? 'badge-crimson' : 'badge-teal'}`}>
                            Danger {loc.danger_level}/5
                          </span>
                        </div>
                        <p className="text-muted" style={{ fontSize: '0.8125rem', marginBottom: '0.75rem' }}>
                          {loc.description}
                        </p>
                        <div className="flex gap-2" style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                          {loc.has_market && <span>🛒 Market</span>}
                          {loc.has_guild && <span>🛡️ Guild</span>}
                          {loc.has_inn && <span>🍺 Inn</span>}
                        </div>
                      </div>

                      <div className="mt-3">
                        {isCurrent ? (
                          <span className="text-gold" style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                            📍 Currently Present
                          </span>
                        ) : (
                          <button
                            className="btn btn-primary"
                            style={{ width: '100%', fontSize: '0.8125rem', padding: '0.5rem' }}
                            onClick={() => travelToLocation(loc.id)}
                            disabled={loading}
                          >
                            Travel Here (1-2 Periods)
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Tab 3: Profile & Attributes */}
          {activeTab === 'profile' && (
            <div>
              <div className="card mb-6">
                <div className="card-header flex justify-between items-center">
                  <h3 className="card-title">Attributes & Mastery</h3>
                  {character.attribute_points > 0 && (
                    <span className="badge badge-gold" style={{ fontSize: '0.875rem' }}>
                      {character.attribute_points} Point(s) Available to Allocate
                    </span>
                  )}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
                  {character.attributes.map((attr) => (
                    <div
                      key={attr.name}
                      style={{
                        background: 'var(--color-bg-tertiary)',
                        padding: '1rem',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--color-border-subtle)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase' }}>
                          {attr.name}
                        </div>
                        <div className="text-primary font-bold" style={{ fontSize: '1.25rem' }}>
                          {attr.current_value}
                        </div>
                      </div>

                      {character.attribute_points > 0 && (
                        <button
                          className="btn"
                          style={{
                            padding: '0.25rem 0.5rem',
                            fontSize: '0.875rem',
                            background: 'var(--color-accent-gold)',
                            color: 'var(--color-text-inverse)',
                            fontWeight: 'bold',
                          }}
                          onClick={() => allocateAttributePoint(attr.name, 1)}
                          disabled={loading}
                          title={`Increase ${attr.name} by 1`}
                        >
                          +
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Skills */}
              <div className="card mb-6">
                <div className="card-header">
                  <h3 className="card-title">Developed Skills</h3>
                </div>
                {character.skills.length === 0 ? (
                  <p className="text-muted">No specialized skills developed yet. Perform work or explore to cultivate skills.</p>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '1rem' }}>
                    {character.skills.map((skill) => (
                      <div
                        key={skill.name}
                        style={{
                          background: 'var(--color-bg-tertiary)',
                          padding: '0.875rem',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid var(--color-border-subtle)',
                        }}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <strong className="text-primary" style={{ textTransform: 'capitalize' }}>
                            {skill.name}
                          </strong>
                          <span className="badge badge-teal">Lv. {skill.level}</span>
                        </div>
                        <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                          XP: {skill.experience}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Inventory */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">Inventory</h3>
                </div>
                {character.inventory.length === 0 ? (
                  <p className="text-muted">Empty knapsack.</p>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '1rem' }}>
                    {character.inventory.map((item) => (
                      <div
                        key={item.item_id}
                        style={{
                          background: 'var(--color-bg-tertiary)',
                          padding: '0.875rem',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid var(--color-border-subtle)',
                        }}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <strong className="text-primary">{item.name}</strong>
                          <span className="badge">x{item.quantity}</span>
                        </div>
                        <p className="text-muted" style={{ fontSize: '0.8125rem', marginBottom: '0.5rem' }}>
                          {item.description}
                        </p>
                        <div className="flex justify-between items-center">
                          <span className="text-gold" style={{ fontSize: '0.75rem' }}>
                            Value: {item.value}g
                          </span>
                          <button
                            className="btn"
                            style={{
                              padding: '0.25rem 0.5rem',
                              fontSize: '0.75rem',
                              background: 'var(--color-bg-elevated)',
                              color: 'var(--color-accent-gold)',
                            }}
                            onClick={() => useInventoryItem(item.item_id, 1)}
                            disabled={loading}
                          >
                            Use
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tab 4: NPCs & Dialogue */}
          {activeTab === 'npcs' && (
            <div>
              <h3 className="font-display text-gold mb-3" style={{ fontSize: '1.25rem' }}>
                Local Inhabitants — {currentLocation?.location?.name}
              </h3>

              {npcDialogue && (
                <div className="alert mb-4" style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-accent-gold)' }}>
                  <p className="text-gold font-bold mb-1">{npcDialogue.npcName} speaks:</p>
                  <p className="text-primary" style={{ fontStyle: 'italic', margin: 0 }}>
                    "{npcDialogue.line}"
                  </p>
                </div>
              )}

              {locationNpcs.length === 0 ? (
                <p className="text-muted">No notable figures present here at this hour.</p>
              ) : (
                <div className="grid-cards">
                  {locationNpcs.map((npc) => (
                    <div key={npc.id} className="action-card">
                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <h4 className="font-display text-primary" style={{ fontSize: '1.05rem' }}>
                            {npc.name}
                          </h4>
                          <span className="badge badge-teal">{npc.relationship_tier}</span>
                        </div>
                        <div className="text-gold" style={{ fontSize: '0.8125rem', marginBottom: '0.5rem' }}>
                          {npc.occupation} &bull; {npc.race_name}
                        </div>
                        <div className="flex justify-between text-muted" style={{ fontSize: '0.75rem' }}>
                          <span>Affinity: {npc.relationship_value}</span>
                          <span>Trust: {npc.trust_level}/100</span>
                        </div>
                      </div>

                      <div className="flex gap-2 mt-2">
                        <button
                          className="btn btn-primary"
                          style={{ flex: 1, fontSize: '0.8125rem', padding: '0.375rem' }}
                          onClick={() => interactWithNpc(npc.id)}
                          disabled={loading}
                        >
                          💬 Talk
                        </button>
                        <button
                          className="btn"
                          style={{
                            flex: 1,
                            fontSize: '0.8125rem',
                            padding: '0.375rem',
                            background: 'var(--color-bg-elevated)',
                            color: 'var(--color-accent-gold)',
                          }}
                          onClick={() => giftNpc(npc.id, { gold_amount: giftGoldAmount })}
                          disabled={loading || currentMoney < giftGoldAmount}
                          title={`Gift ${giftGoldAmount} gold`}
                        >
                          🎁 Gift {giftGoldAmount}g
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 5: Conditions & Treatment */}
          {activeTab === 'conditions' && (
            <div>
              <h3 className="font-display text-gold mb-3" style={{ fontSize: '1.25rem' }}>
                Afflictions, Injuries & Treatments
              </h3>
              {conditions.length === 0 ? (
                <div className="card text-center text-muted" style={{ padding: '2rem' }}>
                  🌱 The body is whole and free of mortal afflictions.
                </div>
              ) : (
                <div className="card-stack">
                  {conditions.map((cond) => (
                    <div
                      key={cond.id}
                      className="card"
                      style={{ borderLeft: '4px solid var(--color-accent-crimson)' }}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h4 className="font-display text-primary">{cond.display_name}</h4>
                          <p className="text-muted" style={{ fontSize: '0.8125rem', margin: 0 }}>
                            {cond.description}
                          </p>
                        </div>
                        <div className="text-right">
                          <span className="badge badge-crimson">Severity {cond.severity}</span>
                          <div className="text-muted" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                            {cond.duration_remaining} days left
                          </div>
                        </div>
                      </div>

                      <div className="mt-3">
                        <button
                          className="btn"
                          style={{
                            fontSize: '0.8125rem',
                            padding: '0.375rem 0.75rem',
                            background: 'var(--color-bg-tertiary)',
                            color: 'var(--color-accent-gold)',
                          }}
                          onClick={() => inspectConditionTreatments(cond.id)}
                          disabled={loading}
                        >
                          Inspect Available Treatments
                        </button>
                      </div>

                      {availableTreatments && availableTreatments.conditionId === cond.id && (
                        <div className="mt-4 pt-3" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
                          <h5 className="font-display text-gold mb-2" style={{ fontSize: '0.875rem' }}>
                            Available Remedies:
                          </h5>
                          <div className="flex flex-col gap-2">
                            {availableTreatments.treatments.map((t) => (
                              <div
                                key={t.id}
                                className="flex justify-between items-center"
                                style={{
                                  background: 'var(--color-bg-secondary)',
                                  padding: '0.5rem 0.75rem',
                                  borderRadius: 'var(--radius-sm)',
                                }}
                              >
                                <div>
                                  <strong className="text-primary" style={{ fontSize: '0.8125rem' }}>
                                    {t.name}
                                  </strong>
                                  <span className="text-muted" style={{ fontSize: '0.75rem', marginLeft: '0.5rem' }}>
                                    Cost: {t.cost_money}g
                                  </span>
                                </div>
                                <button
                                  className="btn"
                                  style={{
                                    fontSize: '0.75rem',
                                    padding: '0.25rem 0.5rem',
                                    background: 'var(--color-accent-teal)',
                                    color: 'white',
                                  }}
                                  onClick={() => treatCondition(cond.id, t.id)}
                                  disabled={loading || currentMoney < t.cost_money}
                                >
                                  Apply Treatment
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Area: Chronicle & Narrative Log */}
        <aside>
          <div className="card" style={{ position: 'sticky', top: '1rem' }}>
            <div className="card-header">
              <h3 className="card-title">Chronicle of Deeds</h3>
            </div>
            <div className="narrative-box">
              {narrativeLogs.length === 0 ? (
                <p className="text-muted" style={{ fontStyle: 'italic', fontSize: '0.8125rem' }}>
                  The chronicle pages await your deeds...
                </p>
              ) : (
                narrativeLogs.map((log, index) => (
                  <div key={index} className="narrative-entry">
                    {log}
                  </div>
                ))
              )}
            </div>
          </div>
        </aside>
      </div>

      {/* --- Event Modal Overlay --- */}
      {activeEvent && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-dialog">
            <div className="flex justify-between items-center mb-3">
              <span className="badge badge-gold">{activeEvent.category} Encounter</span>
            </div>
            <h2 className="font-display text-gold mb-3" style={{ fontSize: '1.5rem' }}>
              {activeEvent.title}
            </h2>
            <p className="text-primary mb-6" style={{ lineHeight: '1.6', fontSize: '0.9375rem' }}>
              {activeEvent.narrative}
            </p>

            <div className="event-choices-list">
              {activeEvent.choices.map((choice) => (
                <button
                  key={choice.id}
                  className="choice-btn"
                  onClick={() => resolveEventChoice(choice.id)}
                  disabled={loading}
                >
                  <div className="flex justify-between items-center mb-1">
                    <strong className="text-primary">{choice.label}</strong>
                    {choice.stat_check && (
                      <span className="badge badge-teal">
                        [{choice.stat_check.attribute.toUpperCase()} DC {choice.stat_check.dc}]
                      </span>
                    )}
                  </div>
                  <p className="text-secondary" style={{ fontSize: '0.8125rem', margin: 0 }}>
                    {choice.description}
                  </p>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
