/** Character Creation Screen.
 *
 * Implements SPEC §12.B:
 * - Name input
 * - Race selection with modifiers and trait preview
 * - Background selection with starting money and skill preview
 * - Gender presentation
 * - Random generation / Reroll
 * - Legacy perk preview when reincarnating
 * - Start Life submission
 */

import React, { useEffect, useState, useMemo } from 'react';
import { useGame } from '../context/GameContext';
import { apiClient } from '../api/client';
import type { BackgroundSummary, RaceSummary } from '../types/game';

const RANDOM_NAMES = [
  'Alden',
  'Lyra',
  'Kaelen',
  'Vesper',
  'Rowan',
  'Sylvia',
  'Gideon',
  'Morrigan',
  'Theron',
  'Aria',
  'Eamon',
  'Isolde',
  'Corvus',
  'Dalia',
  'Baelor',
];

export const CharacterCreationScreen: React.FC = () => {
  const {
    sessionToken,
    reincarnationStatus,
    legacy,
    createCharacter,
    reincarnateCharacter,
    goToScreen,
    loading,
    error,
  } = useGame();

  const [races, setRaces] = useState<RaceSummary[]>([]);
  const [backgrounds, setBackgrounds] = useState<BackgroundSummary[]>([]);

  const [name, setName] = useState('');
  const [selectedRace, setSelectedRace] = useState('human');
  const [selectedBackground, setSelectedBackground] = useState('commoner');
  const [genderPresentation, setGenderPresentation] = useState('non_binary');

  const isReincarnation = Boolean(
    sessionToken && reincarnationStatus && reincarnationStatus.can_reincarnate
  );

  const activeLegacy = legacy || reincarnationStatus?.legacy_preview || null;

  // Load races and backgrounds from backend
  useEffect(() => {
    let isMounted = true;
    Promise.all([apiClient.getRaces(), apiClient.getBackgrounds()])
      .then(([racesData, bgsData]) => {
        if (!isMounted) return;
        setRaces(racesData);
        setBackgrounds(bgsData);
        if (racesData.length > 0) setSelectedRace(racesData[0].name);
        if (bgsData.length > 0) setSelectedBackground(bgsData[0].name);
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  const handleRandomize = () => {
    const randomName = RANDOM_NAMES[Math.floor(Math.random() * RANDOM_NAMES.length)];
    setName(randomName);

    if (races.length > 0) {
      const randomRace = races[Math.floor(Math.random() * races.length)];
      setSelectedRace(randomRace.name);
    }
    if (backgrounds.length > 0) {
      const randomBg = backgrounds[Math.floor(Math.random() * backgrounds.length)];
      setSelectedBackground(randomBg.name);
    }
    const genders = ['male', 'female', 'non_binary'];
    setGenderPresentation(genders[Math.floor(Math.random() * genders.length)]);
  };

  const currentRaceObj = useMemo(
    () => races.find((r) => r.name === selectedRace),
    [races, selectedRace]
  );

  const currentBgObj = useMemo(
    () => backgrounds.find((b) => b.name === selectedBackground),
    [backgrounds, selectedBackground]
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const finalName = name.trim() || RANDOM_NAMES[Math.floor(Math.random() * RANDOM_NAMES.length)];

    if (isReincarnation && sessionToken) {
      await reincarnateCharacter({
        session_token: sessionToken,
        name: finalName,
        race_name: selectedRace,
        background_name: selectedBackground,
        gender_presentation: genderPresentation,
      });
    } else {
      await createCharacter({
        name: finalName,
        race_name: selectedRace,
        background_name: selectedBackground,
        gender_presentation: genderPresentation,
        session_token: sessionToken || undefined,
      });
    }
  };

  return (
    <div className="container" style={{ maxWidth: '840px', margin: '2rem auto' }}>
      <div className="mb-6">
        <h1 className="font-display text-gold" style={{ fontSize: '2rem' }}>
          {isReincarnation
            ? `Transmigration of the Soul — Generation ${(reincarnationStatus?.current_generation ?? 1) + 1}`
            : 'Genesis of a New Life'}
        </h1>
        <p className="text-secondary">
          Choose the mortal vessel and origin for your soul in the kingdom of Eldoria.
        </p>
      </div>

      {isReincarnation && activeLegacy && (
        <div className="alert legacy-box mb-6" style={{ borderLeft: '4px solid var(--color-accent-gold)' }}>
          <h3 className="font-display text-gold" style={{ fontSize: '1.125rem', marginBottom: '0.5rem' }}>
            Ancestral Legacy Inherited (Generation {activeLegacy.unlocked_at_generation})
          </h3>
          <p className="text-secondary mb-2" style={{ fontStyle: 'italic' }}>
            "{activeLegacy.personality_memory || 'Echoes of a past existence stir within your slumbering consciousness.'}"
          </p>
          <div className="flex gap-4" style={{ flexWrap: 'wrap', fontSize: '0.875rem' }}>
            {activeLegacy.bonus_attribute && (
              <span className="badge badge-gold">
                +{activeLegacy.bonus_attribute_value} {activeLegacy.bonus_attribute.toUpperCase()}
              </span>
            )}
            {activeLegacy.skill_affinity && (
              <span className="badge badge-teal">
                +{activeLegacy.skill_affinity_bonus} {activeLegacy.skill_affinity.toUpperCase()} AFFINITY
              </span>
            )}
            {activeLegacy.money_bonus > 0 && (
              <span className="badge badge-gold">+{activeLegacy.money_bonus} STARTING GOLD</span>
            )}
          </div>
        </div>
      )}

      {error && (
        <div className="alert alert-error mb-6">
          <p className="alert-title">Creation Failed</p>
          <p className="alert-message">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="card mb-6">
          <div className="card-header flex justify-between items-center">
            <h2 className="card-title">Identity & Origin</h2>
            <button
              type="button"
              className="btn"
              style={{
                fontSize: '0.875rem',
                padding: '0.375rem 0.75rem',
                background: 'var(--color-bg-tertiary)',
                color: 'var(--color-accent-gold)',
                border: '1px solid var(--color-border-medium)',
              }}
              onClick={handleRandomize}
            >
              🎲 Reroll / Randomize
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
            <div>
              <label htmlFor="char-name" className="label">
                Mortal Name
              </label>
              <input
                id="char-name"
                type="text"
                className="input w-full"
                placeholder="e.g. Rowan the Wanderer"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={50}
              />
            </div>

            <div>
              <label htmlFor="char-gender" className="label">
                Gender Presentation
              </label>
              <select
                id="char-gender"
                className="input w-full"
                value={genderPresentation}
                onChange={(e) => setGenderPresentation(e.target.value)}
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="non_binary">Non-Binary</option>
              </select>
            </div>
          </div>

          {/* Race Selection */}
          <div className="mb-6">
            <label className="label">Lineage & Race</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '0.5rem', marginBottom: '1rem' }}>
              {races.map((r) => (
                <button
                  key={r.name}
                  type="button"
                  onClick={() => setSelectedRace(r.name)}
                  className="btn"
                  style={{
                    padding: '0.75rem 0.5rem',
                    background: selectedRace === r.name ? 'var(--color-bg-elevated)' : 'var(--color-bg-tertiary)',
                    border: `1px solid ${selectedRace === r.name ? 'var(--color-accent-gold)' : 'var(--color-border-medium)'}`,
                    color: selectedRace === r.name ? 'var(--color-accent-gold-light)' : 'var(--color-text-secondary)',
                    fontWeight: selectedRace === r.name ? 'bold' : 'normal',
                  }}
                >
                  {r.display_name}
                </button>
              ))}
            </div>

            {currentRaceObj && (
              <div style={{ background: 'var(--color-bg-tertiary)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}>
                <p className="text-primary mb-2" style={{ fontWeight: 600 }}>
                  {currentRaceObj.racial_trait_name}: <span className="text-secondary" style={{ fontWeight: 400 }}>{currentRaceObj.racial_trait_description}</span>
                </p>
                <p className="text-secondary mb-2" style={{ fontSize: '0.875rem' }}>{currentRaceObj.description}</p>
                <div className="flex gap-2" style={{ flexWrap: 'wrap', fontSize: '0.8125rem' }}>
                  {currentRaceObj.strength_modifier !== 0 && (
                    <span className="badge badge-gold">STR {currentRaceObj.strength_modifier > 0 ? `+${currentRaceObj.strength_modifier}` : currentRaceObj.strength_modifier}</span>
                  )}
                  {currentRaceObj.agility_modifier !== 0 && (
                    <span className="badge badge-teal">AGI {currentRaceObj.agility_modifier > 0 ? `+${currentRaceObj.agility_modifier}` : currentRaceObj.agility_modifier}</span>
                  )}
                  {currentRaceObj.intelligence_modifier !== 0 && (
                    <span className="badge badge-gold">INT {currentRaceObj.intelligence_modifier > 0 ? `+${currentRaceObj.intelligence_modifier}` : currentRaceObj.intelligence_modifier}</span>
                  )}
                  {currentRaceObj.vitality_modifier !== 0 && (
                    <span className="badge badge-crimson">VIT {currentRaceObj.vitality_modifier > 0 ? `+${currentRaceObj.vitality_modifier}` : currentRaceObj.vitality_modifier}</span>
                  )}
                  {currentRaceObj.luck_modifier !== 0 && (
                    <span className="badge badge-gold">LUK {currentRaceObj.luck_modifier > 0 ? `+${currentRaceObj.luck_modifier}` : currentRaceObj.luck_modifier}</span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Background Selection */}
          <div className="mb-6">
            <label className="label">Background & Social Origin</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '0.5rem', marginBottom: '1rem' }}>
              {backgrounds.map((b) => (
                <button
                  key={b.name}
                  type="button"
                  onClick={() => setSelectedBackground(b.name)}
                  className="btn"
                  style={{
                    padding: '0.75rem 0.5rem',
                    background: selectedBackground === b.name ? 'var(--color-bg-elevated)' : 'var(--color-bg-tertiary)',
                    border: `1px solid ${selectedBackground === b.name ? 'var(--color-accent-gold)' : 'var(--color-border-medium)'}`,
                    color: selectedBackground === b.name ? 'var(--color-accent-gold-light)' : 'var(--color-text-secondary)',
                    fontWeight: selectedBackground === b.name ? 'bold' : 'normal',
                  }}
                >
                  {b.display_name}
                </button>
              ))}
            </div>

            {currentBgObj && (
              <div style={{ background: 'var(--color-bg-tertiary)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}>
                <p className="text-secondary mb-2" style={{ fontSize: '0.875rem' }}>{currentBgObj.description}</p>
                <div className="flex gap-4 items-center" style={{ fontSize: '0.875rem' }}>
                  <span className="text-gold" style={{ fontWeight: 600 }}>
                    Starting Gold: {currentBgObj.starting_money} coins
                  </span>
                  <span className="text-muted">
                    Starting Skills: {currentBgObj.starting_skills ? Object.entries(currentBgObj.starting_skills).map(([sk, lv]) => `${sk} (Lv.${lv})`).join(', ') : 'None'}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-between items-center">
          <button
            type="button"
            className="btn"
            style={{ background: 'transparent', color: 'var(--color-text-muted)' }}
            onClick={() => goToScreen('main_menu')}
          >
            ← Return to Void
          </button>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ padding: '0.875rem 2rem', fontSize: '1.125rem' }}
            disabled={loading}
          >
            {loading ? 'Awakening Vessel...' : 'Awaken in Eldoria'}
          </button>
        </div>
      </form>
    </div>
  );
};
