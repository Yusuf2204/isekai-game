"""NPC service package."""

from app.services.npc.service import (
    ensure_npcs_seeded,
    get_all_character_relationships,
    get_npc_profile,
    get_npcs_by_location,
    get_relationship_tier,
    give_gift_to_npc,
    talk_to_npc,
)

__all__ = [
    "ensure_npcs_seeded",
    "get_all_character_relationships",
    "get_npc_profile",
    "get_npcs_by_location",
    "get_relationship_tier",
    "give_gift_to_npc",
    "talk_to_npc",
]
