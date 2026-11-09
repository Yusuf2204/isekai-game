"""Tests for world seed data completeness and idempotency."""

import pytest
from sqlalchemy import select, func

from app.models.world import Kingdom, Region, Location, Race, Background, Enemy
from app.models.enums import RegionName, RaceName, BackgroundName, EnemyType
from app.services.world.seed import (
    seed_world,
    seed_races,
    seed_backgrounds,
    seed_enemies,
    KINGDOM_DATA,
    REGIONS_DATA,
    RACES_DATA,
    BACKGROUNDS_DATA,
    ENEMIES_DATA,
)
from app.core.database import recreate_db, get_session


@pytest.mark.asyncio
async def test_seed_world_completeness():
    """Test that seed_world creates all expected kingdom, regions, and locations."""
    # Initialize fresh database
    await recreate_db()

    async with get_session() as session:
        result = await seed_world(session)

    # Verify kingdom
    assert result["kingdom"] == "Eldoria"

    # Verify 3 regions
    assert len(result["regions"]) == 3
    region_names = {r.split(" — ")[0].lower() for r in result["regions"]}
    assert region_names == {"aetheria", "valdren", "elarion"}

    # Verify 7 locations (5-8 as per SPEC)
    assert 5 <= result["locations_count"] <= 8
    assert result["locations_count"] == 7


@pytest.mark.asyncio
async def test_seed_world_idempotency():
    """Test that running seed_world twice creates no duplicates."""
    await recreate_db()

    async with get_session() as session:
        # First run
        result1 = await seed_world(session)

        # Count records after first run
        kingdom_count_1 = await session.scalar(select(func.count(Kingdom.id)))
        region_count_1 = await session.scalar(select(func.count(Region.id)))
        location_count_1 = await session.scalar(select(func.count(Location.id)))

        # Second run
        result2 = await seed_world(session)

        # Count records after second run
        kingdom_count_2 = await session.scalar(select(func.count(Kingdom.id)))
        region_count_2 = await session.scalar(select(func.count(Region.id)))
        location_count_2 = await session.scalar(select(func.count(Location.id)))

    # Counts should be identical
    assert kingdom_count_1 == kingdom_count_2 == 1
    assert region_count_1 == region_count_2 == 3
    assert location_count_1 == location_count_2 == 7

    # Results should be identical
    assert result1 == result2


@pytest.mark.asyncio
async def test_kingdom_data_integrity():
    """Test that kingdom has correct data."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

        result = await session.execute(select(Kingdom).where(Kingdom.name == "Eldoria"))
        kingdom = result.scalar_one()

    assert kingdom.name == KINGDOM_DATA["name"]
    assert kingdom.description == KINGDOM_DATA["description"]
    assert kingdom.lore == KINGDOM_DATA["lore"]


@pytest.mark.asyncio
async def test_regions_data_integrity():
    """Test that all three regions have correct data and relationships."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

        # Get kingdom
        result = await session.execute(select(Kingdom).where(Kingdom.name == "Eldoria"))
        kingdom = result.scalar_one()

        # Get regions
        result = await session.execute(
            select(Region).where(Region.kingdom_id == kingdom.id)
        )
        regions = list(result.scalars().all())

    assert len(regions) == 3

    # Verify each region matches expected data
    region_map = {r.name: r for r in regions}
    expected_names = {RegionName.AETHERIA, RegionName.VALDREN, RegionName.ELARION}
    assert set(region_map.keys()) == expected_names

    for i, expected in enumerate(REGIONS_DATA):
        region = region_map[expected["name"]]
        assert region.kingdom_id == kingdom.id
        assert region.display_name == expected["display_name"]
        assert region.description == expected["description"]
        assert region.danger_level == expected["danger_level"]


@pytest.mark.asyncio
async def test_locations_data_integrity():
    """Test that all locations have correct data and relationships."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

        # Get all regions
        result = await session.execute(select(Region))
        regions = list(result.scalars().all())
        region_map = {r.name: r for r in regions}

        # Get all locations
        result = await session.execute(select(Location))
        locations = list(result.scalars().all())

    assert len(locations) == 7

    # Group locations by region
    locs_by_region = {}
    for loc in locations:
        region_name = None
        for rname, robj in region_map.items():
            if robj.id == loc.region_id:
                region_name = rname
                break
        if region_name not in locs_by_region:
            locs_by_region[region_name] = []
        locs_by_region[region_name].append(loc)

    # Verify distribution: Aetheria=3, Valdren=2, Elarion=2
    assert len(locs_by_region.get(RegionName.AETHERIA, [])) == 3
    assert len(locs_by_region.get(RegionName.VALDREN, [])) == 2
    assert len(locs_by_region.get(RegionName.ELARION, [])) == 2

    # Verify each location has required fields
    for loc in locations:
        assert loc.name
        assert loc.description
        assert loc.location_type
        assert 1 <= loc.danger_level <= 5
        assert loc.population >= 0
        assert isinstance(loc.has_guild, bool)
        assert isinstance(loc.has_market, bool)
        assert isinstance(loc.has_inn, bool)
        assert isinstance(loc.available_activities, list)


@pytest.mark.asyncio
async def test_foreign_key_relationships():
    """Test that all foreign key relationships are valid."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

        # Kingdom -> Regions
        result = await session.execute(select(Kingdom).where(Kingdom.name == "Eldoria"))
        kingdom = result.scalar_one()

        result = await session.execute(
            select(Region).where(Region.kingdom_id == kingdom.id)
        )
        regions = list(result.scalars().all())

        for region in regions:
            assert region.kingdom_id == kingdom.id
            # Verify back-reference works
            assert region.kingdom.id == kingdom.id

        # Regions -> Locations
        for region in regions:
            result = await session.execute(
                select(Location).where(Location.region_id == region.id)
            )
            locations = list(result.scalars().all())

            for location in locations:
                assert location.region_id == region.id
                # Verify back-reference works
                assert location.region.id == region.id


@pytest.mark.asyncio
async def test_races_completeness():
    """Test that seed_races creates all 6 expected races."""
    await recreate_db()

    async with get_session() as session:
        races = await seed_races(session)

    assert len(races) == 6
    race_names = {race.name for race in races}
    expected_names = {
        RaceName.HUMAN,
        RaceName.ELF,
        RaceName.BEASTKIN,
        RaceName.DWARF,
        RaceName.DRAGONKIN,
        RaceName.DEMONKIN,
    }
    assert race_names == expected_names


@pytest.mark.asyncio
async def test_races_idempotency():
    """Test that running seed_races twice creates no duplicates."""
    await recreate_db()

    async with get_session() as session:
        # First run
        races1 = await seed_races(session)
        count1 = await session.scalar(select(func.count(Race.id)))

        # Second run
        races2 = await seed_races(session)
        count2 = await session.scalar(select(func.count(Race.id)))

    assert count1 == count2 == 6
    assert len(races1) == len(races2) == 6


@pytest.mark.asyncio
async def test_races_data_integrity():
    """Test that all races have correct data."""
    await recreate_db()

    async with get_session() as session:
        await seed_races(session)

        result = await session.execute(select(Race))
        races = list(result.scalars().all())

    assert len(races) == 6

    race_map = {race.name: race for race in races}

    # Verify each race matches expected data
    for expected in RACES_DATA:
        race = race_map[expected["name"]]
        assert race.display_name == expected["display_name"]
        assert race.description == expected["description"]
        assert race.lore == expected["lore"]
        assert race.strength_modifier == expected["strength_modifier"]
        assert race.agility_modifier == expected["agility_modifier"]
        assert race.intelligence_modifier == expected["intelligence_modifier"]
        assert race.vitality_modifier == expected["vitality_modifier"]
        assert race.luck_modifier == expected["luck_modifier"]
        assert race.racial_trait_name == expected["racial_trait_name"]
        assert race.racial_trait_description == expected["racial_trait_description"]
        assert race.social_stigma == expected["social_stigma"]
        assert race.social_privilege == expected["social_privilege"]
        assert race.base_strength == expected["base_strength"]
        assert race.base_agility == expected["base_agility"]
        assert race.base_intelligence == expected["base_intelligence"]
        assert race.base_vitality == expected["base_vitality"]
        assert race.base_luck == expected["base_luck"]

    # Verify specific race characteristics from SPEC
    human = race_map[RaceName.HUMAN]
    assert human.strength_modifier == 0
    assert human.agility_modifier == 0
    assert human.intelligence_modifier == 0
    assert human.vitality_modifier == 0
    assert human.luck_modifier == 0

    elf = race_map[RaceName.ELF]
    assert elf.intelligence_modifier == 2
    assert elf.agility_modifier == 1

    beastkin = race_map[RaceName.BEASTKIN]
    assert beastkin.agility_modifier == 2

    dwarf = race_map[RaceName.DWARF]
    assert dwarf.vitality_modifier == 2

    dragonkin = race_map[RaceName.DRAGONKIN]
    assert dragonkin.strength_modifier == 2

    demonkin = race_map[RaceName.DEMONKIN]
    assert demonkin.luck_modifier == 2
    assert demonkin.intelligence_modifier == 1
    assert demonkin.social_stigma == -4  # Severe discrimination


@pytest.mark.asyncio
async def test_backgrounds_completeness():
    """Test that seed_backgrounds creates all 5 expected backgrounds."""
    await recreate_db()

    async with get_session() as session:
        backgrounds = await seed_backgrounds(session)

    assert len(backgrounds) == 5
    bg_names = {bg.name for bg in backgrounds}
    expected_names = {
        BackgroundName.COMMONER,
        BackgroundName.MERCHANT_FAMILY,
        BackgroundName.ORPHAN,
        BackgroundName.NOBLE_DESCENDANT,
        BackgroundName.FORMER_SLAVE,
    }
    assert bg_names == expected_names


@pytest.mark.asyncio
async def test_backgrounds_idempotency():
    """Test that running seed_backgrounds twice creates no duplicates."""
    await recreate_db()

    async with get_session() as session:
        # First run
        bgs1 = await seed_backgrounds(session)
        count1 = await session.scalar(select(func.count(Background.id)))

        # Second run
        bgs2 = await seed_backgrounds(session)
        count2 = await session.scalar(select(func.count(Background.id)))

    assert count1 == count2 == 5
    assert len(bgs1) == len(bgs2) == 5


@pytest.mark.asyncio
async def test_backgrounds_data_integrity():
    """Test that all backgrounds have correct data."""
    await recreate_db()

    async with get_session() as session:
        await seed_backgrounds(session)

        result = await session.execute(select(Background))
        backgrounds = list(result.scalars().all())

    assert len(backgrounds) == 5

    bg_map = {bg.name: bg for bg in backgrounds}

    # Verify each background matches expected data
    for expected in BACKGROUNDS_DATA:
        bg = bg_map[expected["name"]]
        assert bg.display_name == expected["display_name"]
        assert bg.description == expected["description"]
        assert bg.lore == expected["lore"]
        assert bg.starting_money == expected["starting_money"]
        assert bg.starting_items == expected["starting_items"]
        assert bg.strength_bonus == expected["strength_bonus"]
        assert bg.agility_bonus == expected["agility_bonus"]
        assert bg.intelligence_bonus == expected["intelligence_bonus"]
        assert bg.vitality_bonus == expected["vitality_bonus"]
        assert bg.luck_bonus == expected["luck_bonus"]
        assert bg.starting_skills == expected["starting_skills"]
        assert bg.reputation_modifier == expected["reputation_modifier"]
        assert bg.noble_favor == expected["noble_favor"]
        assert bg.common_favor == expected["common_favor"]
        assert bg.dialogue_tags == expected["dialogue_tags"]

    # Verify specific background characteristics from SPEC
    commoner = bg_map[BackgroundName.COMMONER]
    assert commoner.starting_money == 50
    assert commoner.common_favor == 2

    merchant = bg_map[BackgroundName.MERCHANT_FAMILY]
    assert merchant.starting_money == 200
    assert merchant.starting_skills["trading"] == 2

    orphan = bg_map[BackgroundName.ORPHAN]
    assert orphan.starting_money == 10
    assert orphan.starting_skills["survival"] == 2
    assert orphan.noble_favor == -2

    noble = bg_map[BackgroundName.NOBLE_DESCENDANT]
    assert noble.starting_money == 300
    assert noble.noble_favor == 3
    assert noble.common_favor == -2

    slave = bg_map[BackgroundName.FORMER_SLAVE]
    assert slave.starting_money == 20
    assert slave.noble_favor == -3
    assert slave.common_favor == 2


@pytest.mark.asyncio
async def test_seed_world_includes_races_and_backgrounds():
    """Test that seed_world now includes races and backgrounds in its result."""
    await recreate_db()

    async with get_session() as session:
        result = await seed_world(session)

    # Check that the result includes races and backgrounds
    assert "races_count" in result
    assert "races" in result
    assert "backgrounds_count" in result
    assert "backgrounds" in result

    assert result["races_count"] == 6
    assert result["backgrounds_count"] == 5

    expected_races = {"Human", "Elf", "Beastkin", "Dwarf", "Dragonkin", "Demonkin"}
    assert set(result["races"]) == expected_races

    expected_backgrounds = {
        "Commoner",
        "Merchant Family",
        "Orphan",
        "Noble Descendant",
        "Former Slave",
    }
    assert set(result["backgrounds"]) == expected_backgrounds


@pytest.mark.asyncio
async def test_enemies_completeness():
    """Test that seed_enemies creates all 5 expected enemies."""
    await recreate_db()

    async with get_session() as session:
        enemies = await seed_enemies(session)

    assert len(enemies) == 5
    enemy_names = {enemy.name for enemy in enemies}
    expected_names = {
        EnemyType.SLIME,
        EnemyType.GOBLIN,
        EnemyType.DIRE_WOLF,
        EnemyType.SKELETON,
        EnemyType.CORRUPTED_BEAST,
    }
    assert enemy_names == expected_names


@pytest.mark.asyncio
async def test_enemies_idempotency():
    """Test that running seed_enemies twice creates no duplicates."""
    await recreate_db()

    async with get_session() as session:
        # First run
        enemies1 = await seed_enemies(session)
        count1 = await session.scalar(select(func.count(Enemy.id)))

        # Second run
        enemies2 = await seed_enemies(session)
        count2 = await session.scalar(select(func.count(Enemy.id)))

    assert count1 == count2 == 5
    assert len(enemies1) == len(enemies2) == 5


@pytest.mark.asyncio
async def test_enemies_data_integrity():
    """Test that all enemies have correct data."""
    await recreate_db()

    async with get_session() as session:
        await seed_enemies(session)

        result = await session.execute(select(Enemy))
        enemies = list(result.scalars().all())

    assert len(enemies) == 5

    enemy_map = {enemy.name: enemy for enemy in enemies}

    # Verify each enemy matches expected data
    for expected in ENEMIES_DATA:
        enemy = enemy_map[expected["name"]]
        assert enemy.display_name == expected["display_name"]
        assert enemy.description == expected["description"]
        assert enemy.lore == expected["lore"]
        assert enemy.base_strength == expected["base_strength"]
        assert enemy.base_agility == expected["base_agility"]
        assert enemy.base_intelligence == expected["base_intelligence"]
        assert enemy.base_vitality == expected["base_vitality"]
        assert enemy.base_luck == expected["base_luck"]
        assert enemy.base_health == expected["base_health"]
        assert enemy.base_attack == expected["base_attack"]
        assert enemy.base_defense == expected["base_defense"]
        assert enemy.base_evasion == expected["base_evasion"]
        assert enemy.health_per_level == expected["health_per_level"]
        assert enemy.attack_per_level == expected["attack_per_level"]
        assert enemy.defense_per_level == expected["defense_per_level"]
        assert enemy.experience_reward == expected["experience_reward"]
        assert enemy.money_reward_min == expected["money_reward_min"]
        assert enemy.money_reward_max == expected["money_reward_max"]
        assert enemy.possible_loot == expected["possible_loot"]
        assert enemy.min_level == expected["min_level"]
        assert enemy.max_level == expected["max_level"]
        assert enemy.encounter_weight == expected["encounter_weight"]
        assert enemy.preferred_regions == expected["preferred_regions"]

    # Verify specific enemy characteristics from SPEC
    slime = enemy_map[EnemyType.SLIME]
    assert slime.min_level == 1
    assert slime.max_level == 3
    assert slime.base_health == 25

    goblin = enemy_map[EnemyType.GOBLIN]
    assert goblin.min_level == 1
    assert goblin.max_level == 4
    assert "valdren" in goblin.preferred_regions

    dire_wolf = enemy_map[EnemyType.DIRE_WOLF]
    assert dire_wolf.min_level == 2
    assert dire_wolf.max_level == 6
    assert dire_wolf.base_health == 45

    skeleton = enemy_map[EnemyType.SKELETON]
    assert skeleton.min_level == 3
    assert skeleton.max_level == 7
    assert skeleton.preferred_regions == ["valdren"]

    corrupted_beast = enemy_map[EnemyType.CORRUPTED_BEAST]
    assert corrupted_beast.min_level == 5
    assert corrupted_beast.max_level == 10
    assert corrupted_beast.base_health == 70
    assert corrupted_beast.preferred_regions == ["elarion"]


@pytest.mark.asyncio
async def test_enemies_enum_values():
    """Test that all enemies use valid EnemyType enum values."""
    await recreate_db()

    async with get_session() as session:
        await seed_enemies(session)

        result = await session.execute(select(Enemy))
        enemies = list(result.scalars().all())

    for enemy in enemies:
        # Verify the name is a valid EnemyType enum
        assert enemy.name in EnemyType
        # Verify preferred_regions contains valid region names
        for region in enemy.preferred_regions:
            assert region in ["aetheria", "valdren", "elarion"]


@pytest.mark.asyncio
async def test_seed_world_includes_enemies():
    """Test that seed_world now includes enemies in its result."""
    await recreate_db()

    async with get_session() as session:
        result = await seed_world(session)

    # Check that the result includes enemies
    assert "enemies_count" in result
    assert "enemies" in result

    assert result["enemies_count"] == 5

    expected_enemies = {"Slime", "Goblin", "Dire Wolf", "Skeleton", "Corrupted Beast"}
    assert set(result["enemies"]) == expected_enemies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
