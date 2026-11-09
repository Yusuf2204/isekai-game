"""World seed data for static kingdom, regions, locations, races, and backgrounds."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world import Kingdom, Region, Location, Race, Background, Enemy
from app.models.enums import RegionName, RaceName, BackgroundName, EnemyType


# Kingdom data
KINGDOM_DATA = {
    "name": "Eldoria",
    "description": (
        "An ancient kingdom of soaring spires and shadowed alleyways, "
        "Eldoria stands at a crossroads of magic and steel. Once a beacon of "
        "prosperity, it now trembles under political intrigue, widening "
        "inequality, and the encroaching darkness beyond its borders."
    ),
    "lore": (
        "Founded three centuries ago by the First King Aldric the Radiant, "
        "Eldoria was built upon a ley line nexus where the veil between "
        "worlds grows thin. The royal line has guarded this secret, using "
        "the nexus's power to fuel the kingdom's golden age. But the current "
        "monarch, King Valerius III, grows old and heirless. Noble houses "
        "scheme in gilded halls while the common folk suffer rising taxes and "
        "monster raids. In the sacred forest, ancient spirits stir. In the "
        "frontier mines, something old and hungry wakes. The nexus pulses "
        "with unstable energy, calling to souls from other worlds—souls that "
        "might tip the balance, or be crushed by it."
    ),
}

# Region data
REGIONS_DATA = [
    {
        "name": RegionName.AETHERIA,
        "display_name": "Aetheria — The Royal Capital",
        "description": (
            "The beating heart of Eldoria, where marble palaces tower over "
            "crowded tenements. The Royal Palace dominates the skyline, its "
            "spires wrapped in perpetual magical light. The Adventurer Guild "
            "headquarters hums with desperate souls seeking fortune, while the "
            "Magic Academy's towers pierce the clouds. Merchant caravans clog "
            "the Grand Bazaar, and the River Lumin flows clear through the "
            "noble districts before turning murky in the slums. Here, "
            "politics is a blood sport played with smiles and poisoned wine."
        ),
        "danger_level": 1,
    },
    {
        "name": RegionName.VALDREN,
        "display_name": "Valdren — The Frontier Marches",
        "description": (
            "A harsh land of wind-scoured hills, iron mines, and forgotten "
            "ruins. The frontier settlements are built from rough timber and "
            "stone, huddled behind palisades against the night. Adventurer "
            "outposts dot the trade roads, offering uneasy rest to those "
            "foolish or brave enough to venture deeper. Ancient dwarven "
            "holdfasts lie sealed beneath the mountains, their treasures—and "
            "their horrors—untouched for centuries. The Silvervein Mines "
            "produce the kingdom's wealth, but each season claims more lives "
            "to cave-ins, gas pockets, and things that dwell in the dark."
        ),
        "danger_level": 3,
    },
    {
        "name": RegionName.ELARION,
        "display_name": "Elarion — The Whispering Forest",
        "description": (
            "An ancient woodland where sunlight filters through canopy older "
            "than the kingdom itself. The elves guard their hidden villages "
            "with illusion and arrow, tolerating human presence only at "
            "designated waystations. Shrines to forgotten gods dot the forest "
            "floor, their offerings fresh despite centuries of neglect. Rare "
            "herbs and crystals grow in glades where magic pools like water. "
            "But the deep woods belong to older things—corrupted beasts, "
            "vengeful spirits, and the roots of a darkness that remembers "
            "every slight against the natural world."
        ),
        "danger_level": 4,
    },
]

# Location data - 7 locations distributed across 3 regions
# Aetheria (3), Valdren (2), Elarion (2)
LOCATIONS_DATA = [
    # Aetheria locations
    {
        "region_name": RegionName.AETHERIA,
        "name": "Capital City: Luminaris",
        "description": (
            "The sprawling capital where the Royal Palace casts its shadow "
            "over a million souls. White marble and gold leaf adorn the noble "
            "quarters, while the Lower Ward festers in perpetual twilight. "
            "The Grand Bazaar never sleeps, the Adventurer Guild processes "
            "hundreds of contracts daily, and the Magic Academy's students "
            "experiment with forces they barely comprehend. The River Lumin "
            "bisects the city, crossed by seven bridges—each with its own "
            "tolls, its own gangs, its own secrets."
        ),
        "location_type": "city",
        "danger_level": 1,
        "population": 120000,
        "has_guild": True,
        "has_market": True,
        "has_inn": True,
        "available_activities": [
            "explore",
            "work",
            "trade",
            "train",
            "rest",
            "socialize",
            "accept_quest",
            "visit_location",
        ],
    },
    {
        "region_name": RegionName.AETHERIA,
        "name": "Scholar's District: Arcane Athenaeum",
        "description": (
            "A walled enclave within Luminaris where the Magic Academy "
            "dominates. Towers of impossible geometry house libraries of "
            "forbidden knowledge, laboratories hum with volatile experiments, "
            "and students from across the realm duel with cantrips in "
            "courtyards warded against permanent damage. The Athenaeum's "
            "restricted archives supposedly contain records of every soul "
            "ever reincarnated into Eldoria—a secret the Archmage guards "
            "with lethal dedication."
        ),
        "location_type": "academy",
        "danger_level": 2,
        "population": 3000,
        "has_guild": False,
        "has_market": True,
        "has_inn": True,
        "available_activities": [
            "explore",
            "train",
            "rest",
            "socialize",
            "visit_location",
        ],
    },
    {
        "region_name": RegionName.AETHERIA,
        "name": "Merchant Quarter: Gilded Bazaar",
        "description": (
            "A labyrinth of covered streets where spices from southern "
            "continents mingle with dwarven steel and elven silk. The "
            "Merchant Princes operate from opulent offices above the market, "
            "their ledgers recording debts owed by kings and beggars alike. "
            "Everything has a price here—information, loyalty, even clean "
            "identities for those fleeing past mistakes. The quarter's "
            "inns cater to caravan guards and traveling merchants, their "
            "cellars connecting to smuggling tunnels older than the city walls."
        ),
        "location_type": "market",
        "danger_level": 1,
        "population": 15000,
        "has_guild": False,
        "has_market": True,
        "has_inn": True,
        "available_activities": [
            "explore",
            "work",
            "trade",
            "rest",
            "socialize",
            "visit_location",
        ],
    },
    # Valdren locations
    {
        "region_name": RegionName.VALDREN,
        "name": "Frontier Outpost: Ironwatch",
        "description": (
            "A fortified town built around the entrance to the Silvervein "
            "Mines. Wooden palisades reinforced with iron bands surround "
            "rows of barracks, forges, and taverns that never close. Miners "
            "and adventurers drink together in uneasy camaraderie, sharing "
            "rumors of deep-delving horrors and veins of mithral that gleam "
            "like captured starlight. The outpost commander, a scarred "
            "veteran named Captain Renauld, runs Ironwatch with military "
            "efficiency and a healthy distrust of nobility's promises."
        ),
        "location_type": "outpost",
        "danger_level": 3,
        "population": 2500,
        "has_guild": True,
        "has_market": True,
        "has_inn": True,
        "available_activities": [
            "explore",
            "work",
            "trade",
            "train",
            "rest",
            "socialize",
            "accept_quest",
            "hunt_monsters",
            "visit_location",
        ],
    },
    {
        "region_name": RegionName.VALDREN,
        "name": "Ruins of Khaz-Dul",
        "description": (
            "The shattered remains of a dwarven stronghold, abandoned three "
            "centuries ago when the deep delving broke into a cavern of "
            "living shadow. The upper halls have been reclaimed by "
            "adventurers as a staging ground, their campfires lighting "
            "corridors where dwarven runes still glow faintly. Deeper "
            "levels remain unexplored—expeditions that venture too far "
            "return changed, or not at all. The ruins are rich in "
            "dwarven-crafted arms and armor, but every artifact carries "
            "the weight of a civilization's final mistake."
        ),
        "location_type": "ruins",
        "danger_level": 4,
        "population": 0,
        "has_guild": False,
        "has_market": False,
        "has_inn": False,
        "available_activities": ["explore", "hunt_monsters", "visit_location"],
    },
    # Elarion locations
    {
        "region_name": RegionName.ELARION,
        "name": "Elven Enclave: Sylvaris",
        "description": (
            "A hidden village woven into the boughs of massive world-trees, "
            "connected by rope bridges and platforms that sway with the wind. "
            "The elves of Sylvaris are wary of outsiders but not hostile—"
            "those who prove respectful may trade for moon-silver weapons, "
            "healing draughts, and knowledge of the forest's secret paths. "
            "The village centers on the Shrine of the First Light, where an "
            "eternal flame burns without fuel, tended by priestesses who "
            "speak in riddles and see possible futures in the smoke."
        ),
        "location_type": "village",
        "danger_level": 2,
        "population": 800,
        "has_guild": False,
        "has_market": True,
        "has_inn": True,
        "available_activities": [
            "explore",
            "trade",
            "train",
            "rest",
            "socialize",
            "visit_location",
        ],
    },
    {
        "region_name": RegionName.ELARION,
        "name": "Ancient Grove: Moonwell Sanctuary",
        "description": (
            "A circular clearing where silver moonlight pools in a natural "
            "stone basin—the Moonwell, source of the forest's purest magic. "
            "Druids and rangers tend the grove, harvesting rare reagents "
            "under strict ritual. The sanctuary is neutral ground; even "
            "corrupted beasts hesitate to enter its wards. But the wards "
            "are failing. Each season, the Moonwell's light dims, and "
            "something vast stirs in the roots beneath, dreaming of "
            "reclaiming what was stolen when the First King bound the land's "
            "heart to his crown."
        ),
        "location_type": "shrine",
        "danger_level": 3,
        "population": 50,
        "has_guild": False,
        "has_market": False,
        "has_inn": False,
        "available_activities": ["explore", "train", "rest", "visit_location"],
    },
]

# Race data - 6 playable races as per SPEC
RACES_DATA = [
    {
        "name": RaceName.HUMAN,
        "display_name": "Human",
        "description": (
            "The most numerous and adaptable race in Eldoria. Humans possess no "
            "extraordinary gifts, but their versatility allows them to thrive "
            "in any environment and pursue any path. They are the bridge between "
            "races, welcomed in all lands yet belonging fully to none."
        ),
        "lore": (
            "Humans arrived in Eldoria centuries ago as refugees from a dying "
            "world across the sea. The First King Aldric welcomed them, and "
            "they repaid his kindness by helping build the kingdom into a "
            "prosperous realm. Today, humans hold positions at every level of "
            "society—from the royal court to the humblest farmstead. Their "
            "short lifespans drive an urgency to achieve, to leave a mark "
            "before their brief candle gutters out. Some say this is their "
            "greatest strength: the ability to change the world in a single "
            "generation."
        ),
        "strength_modifier": 0,
        "agility_modifier": 0,
        "intelligence_modifier": 0,
        "vitality_modifier": 0,
        "luck_modifier": 0,
        "racial_trait_name": "Adaptable Spirit",
        "racial_trait_description": (
            "Humans gain a +1 bonus to any one attribute of their choice at "
            "character creation, reflecting their boundless potential."
        ),
        "social_stigma": 0,
        "social_privilege": 1,
        "base_strength": 10,
        "base_agility": 10,
        "base_intelligence": 10,
        "base_vitality": 10,
        "base_luck": 10,
    },
    {
        "name": RaceName.ELF,
        "display_name": "Elf",
        "description": (
            "Tall, graceful, and long-lived, elves are the ancient custodians "
            "of Eldoria's deepest magic. Their minds are naturally attuned to "
            "the arcane, and their senses perceive what others cannot. In the "
            "Whispering Forest of Elarion, they guard secrets older than the "
            "kingdom itself."
        ),
        "lore": (
            "Elves were the first children of the World Tree, born from its "
            "silver leaves when the world was young. They watched the rise and "
            "fall of empires before humans ever set foot on these shores. The "
            "binding of the ley lines by the First King wounded the World Tree, "
            "and elves have never fully forgiven humanity for it. Those who "
            "leave Elarion's shelter do so as exiles, scholars, or spies—"
            "their presence in human lands always watched, their motives "
            "forever questioned."
        ),
        "strength_modifier": -1,
        "agility_modifier": 1,
        "intelligence_modifier": 2,
        "vitality_modifier": -1,
        "luck_modifier": 0,
        "racial_trait_name": "Arcane Attunement",
        "racial_trait_description": (
            "Elves recover mana faster and gain a +2 bonus to Magic skill "
            "checks. They can sense magical auras within 30 feet."
        ),
        "social_stigma": 1,
        "social_privilege": 2,
        "base_strength": 8,
        "base_agility": 12,
        "base_intelligence": 14,
        "base_vitality": 8,
        "base_luck": 10,
    },
    {
        "name": RaceName.BEASTKIN,
        "display_name": "Beastkin",
        "description": (
            "Humanoids with bestial features—ears, tails, claws, or fur—"
            "beastkin possess heightened senses and supernatural agility. "
            "They are swift hunters and fierce survivors, equally at home in "
            "city alleyways and wild forests. Their instincts guide them "
            "where logic fails."
        ),
        "lore": (
            "Beastkin trace their lineage to the Primordial Beasts that "
            "roamed Eldoria before civilization. Some say they were blessed "
            "by the Beast Gods; others whisper of cursed bloodlines. In the "
            "frontier regions, beastkin are valued as scouts and trackers. "
            "In the capital, they face quiet discrimination—barred from "
            "certain guilds, watched by city guards. Many embrace the "
            "adventurer's life, where skill matters more than lineage."
        ),
        "strength_modifier": 1,
        "agility_modifier": 2,
        "intelligence_modifier": -1,
        "vitality_modifier": 0,
        "luck_modifier": 1,
        "racial_trait_name": "Keen Senses",
        "racial_trait_description": (
            "Beastkin gain advantage on perception checks and cannot be "
            "surprised while conscious. They gain +2 to Survival and "
            "Stealth skills."
        ),
        "social_stigma": 1,
        "social_privilege": 0,
        "base_strength": 11,
        "base_agility": 14,
        "base_intelligence": 9,
        "base_vitality": 10,
        "base_luck": 11,
    },
    {
        "name": RaceName.DWARF,
        "display_name": "Dwarf",
        "description": (
            "Stout, resilient, and master craftsmen, dwarves are the backbone "
            "of Eldoria's industry. Their bodies resist poison and fatigue, "
            "and their hands shape metal and stone with unmatched skill. "
            "A dwarf's word is their bond, and their grudges last generations."
        ),
        "lore": (
            "Dwarves delved the mountains of Valdren long before humans "
            "claimed the surface. The Silvervein Mines were once the heart of "
            "a vast dwarven kingdom, Khaz-Dul, until the deep delving woke "
            "something that drove them from their ancestral halls. Now scattered "
            "in human settlements, dwarves preserve their traditions in "
            "clan-halls and forge-temples. They remember every slight against "
            "their people—and every kindness. A dwarf friend is a friend for "
            "life; a dwarf enemy will hunt your grandchildren."
        ),
        "strength_modifier": 1,
        "agility_modifier": -1,
        "intelligence_modifier": 0,
        "vitality_modifier": 2,
        "luck_modifier": -1,
        "racial_trait_name": "Iron Constitution",
        "racial_trait_description": (
            "Dwarves have advantage on saves against poison, disease, and "
            "fatigue. They gain +2 to Crafting skill and can identify "
            "metal and stone properties by touch."
        ),
        "social_stigma": 0,
        "social_privilege": 1,
        "base_strength": 12,
        "base_agility": 8,
        "base_intelligence": 10,
        "base_vitality": 14,
        "base_luck": 8,
    },
    {
        "name": RaceName.DRAGONKIN,
        "display_name": "Dragonkin",
        "description": (
            "Descendants of ancient draconic bloodlines, dragonkin bear "
            "scales, horns, or slit-pupiled eyes that mark their heritage. "
            "They possess tremendous physical strength and a natural resistance "
            "to magic and elements. Their presence commands respect—and fear."
        ),
        "lore": (
            "When the Dragon Lords ruled the skies, they sometimes took "
            "mortal lovers or were worshipped by cults that performed "
            "blood rituals. The offspring of these unions were the first "
            "dragonkin. In the early kingdom, they served as elite guardians "
            "of the royal line. But as dragon worship faded, so did their "
            "status. Now they are rare, often hiding their features to avoid "
            "superstitious persecution—or flaunting them as mercenaries and "
            "adventurers who trade on their fearsome reputation."
        ),
        "strength_modifier": 2,
        "agility_modifier": 0,
        "intelligence_modifier": 0,
        "vitality_modifier": 1,
        "luck_modifier": -1,
        "racial_trait_name": "Draconic Heritage",
        "racial_trait_description": (
            "Dragonkin have resistance to one element (fire, cold, lightning, "
            "or acid) chosen at character creation. They gain +2 to "
            "Intimidation and a natural armor bonus of +1."
        ),
        "social_stigma": 2,
        "social_privilege": 1,
        "base_strength": 14,
        "base_agility": 10,
        "base_intelligence": 10,
        "base_vitality": 12,
        "base_luck": 8,
    },
    {
        "name": RaceName.DEMONKIN,
        "display_name": "Demonkin",
        "description": (
            "Marked by fiendish ancestry—horns, unusual skin tones, or "
            "glowing eyes—demonkin possess immense magical potential but "
            "face severe discrimination. In a world that fears what it "
            "does not understand, they walk a razor's edge between power "
            "and persecution."
        ),
        "lore": (
            "Demonkin are the result of ancient pacts between desperate "
            "mortals and entities from the Lower Planes. The blood of those "
            "bargains runs thick in their veins. The Church of the Radiant "
            "Light brands them 'spawn of corruption,' and in many regions, "
            "demonkin are legally barred from owning property, holding "
            "office, or even walking the streets after dark. Yet their "
            "innate magic is undeniable—some of the greatest archmages in "
            "history were demonkin who channeled their heritage into "
            "wonders. To be demonkin is to carry a legacy of both "
            "condemnation and greatness."
        ),
        "strength_modifier": 0,
        "agility_modifier": 1,
        "intelligence_modifier": 1,
        "vitality_modifier": -1,
        "luck_modifier": 2,
        "racial_trait_name": "Fiendish Legacy",
        "racial_trait_description": (
            "Demonkin gain +2 to Magic skill and can cast a minor cantrip "
            "at will (chosen at creation). They have resistance to fire and "
            "necrotic damage but take +1 damage from radiant sources."
        ),
        "social_stigma": -4,
        "social_privilege": 0,
        "base_strength": 10,
        "base_agility": 12,
        "base_intelligence": 13,
        "base_vitality": 8,
        "base_luck": 12,
    },
]

# Background data - 5 backgrounds as per SPEC
BACKGROUNDS_DATA = [
    {
        "name": BackgroundName.COMMONER,
        "display_name": "Commoner",
        "description": (
            "Born to farmers, laborers, or craftsfolk in a humble village or "
            "city district. You learned the value of hard work early and know "
            "how to survive on little. The common folk are the backbone of "
            "Eldoria, though the nobility rarely remembers it."
        ),
        "lore": (
            "Your parents worked the land or a trade, teaching you honesty "
            "and perseverance. You've known hunger and you've known the "
            "simple joy of a harvest festival. The nobles in their towers "
            "make laws that affect your life without ever knowing your name. "
            "But you have something they don't: the respect of your neighbors, "
            "calloused hands that build and mend, and the freedom to choose "
            "your own path—even if that path is harder."
        ),
        "starting_money": 50,
        "starting_items": [
            "Simple clothing",
            "Basic tools (trade-specific)",
            "Rations (3 days)",
        ],
        "strength_bonus": 1,
        "agility_bonus": 0,
        "intelligence_bonus": 0,
        "vitality_bonus": 1,
        "luck_bonus": 0,
        "starting_skills": {"survival": 1, "crafting": 1},
        "reputation_modifier": 0,
        "noble_favor": -1,
        "common_favor": 2,
        "dialogue_tags": ["humble", "hardworking", "practical", "community"],
    },
    {
        "name": BackgroundName.MERCHANT_FAMILY,
        "display_name": "Merchant Family",
        "description": (
            "Raised in a family of traders, you grew up counting coins, "
            "negotiating deals, and reading contracts before you could read "
            "books. Money is a language you speak fluently, and connections "
            "are currency more valuable than gold."
        ),
        "lore": (
            "Your family's caravan has traveled the length of Eldoria, from "
            "the spice markets of the south to the iron ports of the north. "
            "You've dined with nobles and haggled with bandits. You know "
            "which roads are safe in which season, which officials accept "
            "'gifts,' and how to spot a counterfeit coin by weight alone. "
            "But the merchant's life is precarious—one bad deal, one bandit "
            "raid, one political shift can ruin generations of work. You "
            "carry that tension in your shoulders, always calculating, "
            "always planning the next venture."
        ),
        "starting_money": 200,
        "starting_items": [
            "Fine clothing",
            "Merchant's ledger",
            "Trade goods (minor)",
            "Rations (5 days)",
        ],
        "strength_bonus": 0,
        "agility_bonus": 1,
        "intelligence_bonus": 1,
        "vitality_bonus": 0,
        "luck_bonus": 1,
        "starting_skills": {"trading": 2, "negotiation": 1},
        "reputation_modifier": 1,
        "noble_favor": 1,
        "common_favor": 1,
        "dialogue_tags": ["wealthy", "connected", "calculating", "well-traveled"],
    },
    {
        "name": BackgroundName.ORPHAN,
        "display_name": "Orphan",
        "description": (
            "You have no family name, no inheritance, and no safety net. "
            "Raised on streets or in overcrowded orphanages, you survived "
            "through wit, speed, and the kindness of strangers—sometimes "
            "genuine, sometimes transactional. The world owes you nothing, "
            "and you've learned to take what you need."
        ),
        "lore": (
            "You don't remember your parents. Perhaps they died of plague, "
            "or war, or simply abandoned you. The orphanage matron called you "
            "a burden; the street gangs called you prey. You learned to "
            "disappear in crowds, to pick a pocket faster than a blink, to "
            "sleep with one eye open. But you also learned who shares their "
            "bread, who looks the other way when you steal an apple, who "
            "teaches you to read by candlelight in a cellar. The streets "
            "made you hard, but they also made you see people clearly. "
            "Now you have a chance to be more than a survivor."
        ),
        "starting_money": 10,
        "starting_items": [
            "Worn clothing",
            "Small keepsake (sentimental value only)",
            "Rations (1 day)",
        ],
        "strength_bonus": 0,
        "agility_bonus": 2,
        "intelligence_bonus": 0,
        "vitality_bonus": 0,
        "luck_bonus": 1,
        "starting_skills": {"survival": 2, "stealth": 1},
        "reputation_modifier": -1,
        "noble_favor": -2,
        "common_favor": 1,
        "dialogue_tags": ["streetwise", "independent", "cautious", "resourceful"],
    },
    {
        "name": BackgroundName.NOBLE_DESCENDANT,
        "display_name": "Noble Descendant",
        "description": (
            "Born to a noble house—perhaps a cadet branch, perhaps the main "
            "line fallen on hard times. You were educated in etiquette, "
            "heraldry, and the subtle arts of court intrigue. Your name opens "
            "doors, but it also paints a target on your back."
        ),
        "lore": (
            "Your family's banner once flew high over estates and armies. "
            "Now, the coffers are dwindling, the lands sold off to pay debts, "
            "and rivals circle like vultures. You were tutored in poetry and "
            "poison, in dance and duel. You know which fork to use for the "
            "fish course and which noble's heir has a gambling problem. But "
            "book learning doesn't feed armies, and court manners don't stop "
            "blades. Some nobles cling to dignity in poverty; others scheme "
            "to restore their house by any means. You must decide which you "
            "will be."
        ),
        "starting_money": 300,
        "starting_items": [
            "Noble attire",
            "Signet ring (house crest)",
            "Letter of introduction",
            "Rations (7 days)",
            "Fine dagger",
        ],
        "strength_bonus": 0,
        "agility_bonus": 0,
        "intelligence_bonus": 2,
        "vitality_bonus": -1,
        "luck_bonus": 1,
        "starting_skills": {"negotiation": 2, "magic": 1},
        "reputation_modifier": 2,
        "noble_favor": 3,
        "common_favor": -2,
        "dialogue_tags": ["educated", "entitled", "political", "refined"],
    },
    {
        "name": BackgroundName.FORMER_SLAVE,
        "display_name": "Former Slave",
        "description": (
            "You were property—bought, sold, and worked until your body "
            "broke or your spirit nearly did. Freedom came through escape, "
            "manumission, or a master's death. The brand or scar remains, "
            "but so does the iron will that survived the unendurable."
        ),
        "lore": (
            "The slave markets of the southern reaches care nothing for "
            "race or background—only muscle, magic, or beauty. You were "
            "taken in a raid, sold for debt, or born into chains. The "
            "overseer's whip taught you endurance; the quiet whispers of "
            "fellow slaves taught you hope. Freedom is unfamiliar, "
            "terrifying, precious. You flinch at raised voices. You hoard "
            "food. You watch exits. But you also know the value of a "
            "promise kept, the strength of those who endure, and the "
            "ferocity of someone with nothing left to lose. The chains are "
            "gone. The fire remains."
        ),
        "starting_money": 20,
        "starting_items": [
            "Simple clothing",
            "Brand/scar (visible)",
            "Rations (2 days)",
            "Shackle key (kept as reminder)",
        ],
        "strength_bonus": 1,
        "agility_bonus": 1,
        "intelligence_bonus": 0,
        "vitality_bonus": 1,
        "luck_bonus": -1,
        "starting_skills": {"survival": 1, "crafting": 1, "healing": 1},
        "reputation_modifier": -1,
        "noble_favor": -3,
        "common_favor": 2,
        "dialogue_tags": ["resilient", "guarded", "empathetic", "determined"],
    },
]

# Enemy data - 5 enemy types as per SPEC §8
ENEMIES_DATA = [
    {
        "name": EnemyType.SLIME,
        "display_name": "Slime",
        "description": (
            "A gelatinous, semi-transparent creature that oozes through "
            "dungeons and sewers. Though mindless, its acidic body dissolves "
            "organic matter on contact. Adventurers often underestimate them, "
            "only to find their armor ruined and boots melted."
        ),
        "lore": (
            "Slimes are the byproduct of alchemical waste and wild magic "
            "runoff collecting in low-lying areas. They possess no intelligence, "
            "only an instinct to consume and grow. Some alchemists prize slime "
            "cores for potion-making, but harvesting them requires caution—"
            "a slime that has consumed enough biomass can split into two, "
            "turning one nuisance into a swarm."
        ),
        "base_strength": 3,
        "base_agility": 4,
        "base_intelligence": 1,
        "base_vitality": 6,
        "base_luck": 2,
        "base_health": 25,
        "base_attack": 4,
        "base_defense": 2,
        "base_evasion": 6,
        "health_per_level": 5,
        "attack_per_level": 1,
        "defense_per_level": 0,
        "experience_reward": 15,
        "money_reward_min": 1,
        "money_reward_max": 5,
        "possible_loot": ["Slime Gel", "Minor Healing Potion"],
        "min_level": 1,
        "max_level": 3,
        "encounter_weight": 20,
        "preferred_regions": ["aetheria", "valdren"],
    },
    {
        "name": EnemyType.GOBLIN,
        "display_name": "Goblin",
        "description": (
            "Small, green-skinned humanoids with oversized ears and cruel "
            "grins. Goblins hunt in packs, using crude weapons and ambush "
            "tactics. Individually weak, they become dangerous when coordinated "
            "by a shaman or chieftain. They loot anything shiny and have a "
            "particular hatred for dwarves."
        ),
        "lore": (
            "Goblins infest the frontier regions, occupying abandoned mines "
            "and ruins. They reproduce rapidly and mature within a year, making "
            "them a persistent nuisance. Some tribes have been known to trade "
            "with unscrupulous merchants, exchanging stolen goods for alcohol "
            "and metal scraps. Their shamans wield crude but effective fire "
            "magic, passed down through oral tradition."
        ),
        "base_strength": 5,
        "base_agility": 7,
        "base_intelligence": 4,
        "base_vitality": 5,
        "base_luck": 5,
        "base_health": 30,
        "base_attack": 6,
        "base_defense": 3,
        "base_evasion": 8,
        "health_per_level": 6,
        "attack_per_level": 1,
        "defense_per_level": 1,
        "experience_reward": 25,
        "money_reward_min": 5,
        "money_reward_max": 15,
        "possible_loot": ["Goblin Ear", "Crude Dagger", "Small Coin Purse"],
        "min_level": 1,
        "max_level": 4,
        "encounter_weight": 18,
        "preferred_regions": ["valdren", "elarion"],
    },
    {
        "name": EnemyType.DIRE_WOLF,
        "display_name": "Dire Wolf",
        "description": (
            "Massive wolves the size of ponies, with fur as dark as midnight "
            "and eyes that gleam with predatory intelligence. They hunt in "
            "coordinated packs, flanking prey and targeting the weak. Their "
            "howl strikes fear into even seasoned travelers. Wounded dire "
            "wolves enter a frenzy, becoming faster and deadlier."
        ),
        "lore": (
            "Dire wolves are not natural beasts—they are the result of "
            "corrupted fey magic seeping from the Whispering Forest into the "
            "frontier. Packs are led by an alpha, typically the largest and "
            "most cunning. They avoid fire and bright light, preferring to "
            "stalk at night. Their pelts are prized by hunters, and their "
            "fangs make potent reagents for strength-enhancing elixirs."
        ),
        "base_strength": 8,
        "base_agility": 9,
        "base_intelligence": 5,
        "base_vitality": 8,
        "base_luck": 4,
        "base_health": 45,
        "base_attack": 9,
        "base_defense": 5,
        "base_evasion": 10,
        "health_per_level": 8,
        "attack_per_level": 2,
        "defense_per_level": 1,
        "experience_reward": 50,
        "money_reward_min": 10,
        "money_reward_max": 25,
        "possible_loot": ["Dire Wolf Pelt", "Dire Fang", "Wolf Meat"],
        "min_level": 2,
        "max_level": 6,
        "encounter_weight": 15,
        "preferred_regions": ["valdren", "elarion"],
    },
    {
        "name": EnemyType.SKELETON,
        "display_name": "Skeleton",
        "description": (
            "Animated bones held together by necromantic energy, wielding "
            "rusted weapons with eerie precision. They feel no pain, know no "
            "fear, and never tire. Arrows and slashing weapons pass through "
            "gaps in their ribs, but blunt weapons shatter bone effectively. "
            "They are often found guarding ancient tombs and cursed ruins."
        ),
        "lore": (
            "Skeletons are the foot soldiers of necromancers and the restless "
            "dead of battlefields where proper rites were denied. The ruins of "
            "Khaz-Dul teem with them—dwarven ancestors risen by the shadow "
            "that drove their kin out. They retain muscle memory from life, "
            "making former soldiers particularly dangerous. Holy magic and "
            "blessed weapons disrupt the animating magic."
        ),
        "base_strength": 7,
        "base_agility": 5,
        "base_intelligence": 3,
        "base_vitality": 10,
        "base_luck": 2,
        "base_health": 40,
        "base_attack": 8,
        "base_defense": 6,
        "base_evasion": 4,
        "health_per_level": 7,
        "attack_per_level": 2,
        "defense_per_level": 1,
        "experience_reward": 45,
        "money_reward_min": 8,
        "money_reward_max": 20,
        "possible_loot": ["Bone Fragment", "Rusted Sword", "Ancient Coin"],
        "min_level": 3,
        "max_level": 7,
        "encounter_weight": 12,
        "preferred_regions": ["valdren"],
    },
    {
        "name": EnemyType.CORRUPTED_BEAST,
        "display_name": "Corrupted Beast",
        "description": (
            "A once-noble creature twisted by dark magic into a monstrosity. "
            "Flesh ripples with unnatural growths, and its eyes burn with "
            "malevolent intelligence. Corrupted beasts are stronger, faster, "
            "and more cunning than their natural counterparts. They radiate an "
            "aura of corruption that sickens those who fight them too long."
        ),
        "lore": (
            "Corruption spreads from the deepest reaches of Elarion, where the "
            "World Tree's roots drink from tainted ley lines. Beasts that "
            "linger too long near these sources undergo horrific transformation. "
            "Some druids believe the corruption can be reversed if caught early, "
            "but most corrupted beasts are too far gone. Their corrupted hearts "
            "are valuable to dark mages, but handling them risks infection."
        ),
        "base_strength": 12,
        "base_agility": 8,
        "base_intelligence": 6,
        "base_vitality": 12,
        "base_luck": 3,
        "base_health": 70,
        "base_attack": 14,
        "base_defense": 8,
        "base_evasion": 7,
        "health_per_level": 10,
        "attack_per_level": 3,
        "defense_per_level": 1,
        "experience_reward": 100,
        "money_reward_min": 20,
        "money_reward_max": 50,
        "possible_loot": ["Corrupted Heart", "Tainted Essence", "Mutated Hide"],
        "min_level": 5,
        "max_level": 10,
        "encounter_weight": 8,
        "preferred_regions": ["elarion"],
    },
]


async def seed_kingdom(session: AsyncSession) -> Kingdom:
    """Seed the kingdom if it doesn't exist. Returns the kingdom."""
    result = await session.execute(
        select(Kingdom).where(Kingdom.name == KINGDOM_DATA["name"])
    )
    kingdom = result.scalar_one_or_none()

    if kingdom is None:
        kingdom = Kingdom(**KINGDOM_DATA)
        session.add(kingdom)
        await session.flush()
        await session.refresh(kingdom)

    return kingdom


async def seed_regions(
    session: AsyncSession, kingdom: Kingdom
) -> dict[RegionName, Region]:
    """Seed regions for the kingdom. Returns a mapping of RegionName to Region."""
    regions = {}

    for region_data in REGIONS_DATA:
        region_name = region_data["name"]
        result = await session.execute(
            select(Region).where(
                Region.kingdom_id == kingdom.id,
                Region.name == region_name,
            )
        )
        region = result.scalar_one_or_none()

        if region is None:
            region = Region(
                kingdom_id=kingdom.id,
                **region_data,
            )
            session.add(region)
            await session.flush()
            await session.refresh(region)

        regions[region_name] = region

    return regions


async def seed_locations(
    session: AsyncSession, regions: dict[RegionName, Region]
) -> list[Location]:
    """Seed locations for the regions. Returns list of created/found locations."""
    locations = []

    for loc_data in LOCATIONS_DATA:
        # Copy to avoid modifying the original data
        loc_data_copy = dict(loc_data)
        region_name = loc_data_copy.pop("region_name")
        region = regions[region_name]

        result = await session.execute(
            select(Location).where(
                Location.region_id == region.id,
                Location.name == loc_data["name"],
            )
        )
        location = result.scalar_one_or_none()

        if location is None:
            location = Location(region_id=region.id, **loc_data_copy)
            session.add(location)
            await session.flush()
            await session.refresh(location)

        locations.append(location)

    return locations


async def seed_races(session: AsyncSession) -> list[Race]:
    """Seed all playable races. Returns list of created/found races."""
    races = []

    for race_data in RACES_DATA:
        race_name = race_data["name"]
        result = await session.execute(select(Race).where(Race.name == race_name))
        race = result.scalar_one_or_none()

        if race is None:
            race = Race(**race_data)
            session.add(race)
            await session.flush()
            await session.refresh(race)

        races.append(race)

    return races


async def seed_backgrounds(session: AsyncSession) -> list[Background]:
    """Seed all character backgrounds. Returns list of created/found backgrounds."""
    backgrounds = []

    for bg_data in BACKGROUNDS_DATA:
        bg_name = bg_data["name"]
        result = await session.execute(
            select(Background).where(Background.name == bg_name)
        )
        background = result.scalar_one_or_none()

        if background is None:
            background = Background(**bg_data)
            session.add(background)
            await session.flush()
            await session.refresh(background)

        backgrounds.append(background)

    return backgrounds


async def seed_enemies(session: AsyncSession) -> list[Enemy]:
    """Seed all enemy types. Returns list of created/found enemies."""
    enemies = []

    for enemy_data in ENEMIES_DATA:
        enemy_name = enemy_data["name"]
        result = await session.execute(select(Enemy).where(Enemy.name == enemy_name))
        enemy = result.scalar_one_or_none()

        if enemy is None:
            enemy = Enemy(**enemy_data)
            session.add(enemy)
            await session.flush()
            await session.refresh(enemy)

        enemies.append(enemy)

    return enemies


async def seed_world(session: AsyncSession) -> dict:
    """
    Seed all static world data (kingdom, regions, locations, races, backgrounds, enemies).
    Idempotent: running multiple times will not create duplicates.
    Returns a summary of what was seeded.
    """
    kingdom = await seed_kingdom(session)
    regions = await seed_regions(session, kingdom)
    locations = await seed_locations(session, regions)
    races = await seed_races(session)
    backgrounds = await seed_backgrounds(session)
    enemies = await seed_enemies(session)

    await session.commit()

    return {
        "kingdom": kingdom.name,
        "regions": [r.display_name for r in regions.values()],
        "locations_count": len(locations),
        "locations": [loc.name for loc in locations],
        "races_count": len(races),
        "races": [race.display_name for race in races],
        "backgrounds_count": len(backgrounds),
        "backgrounds": [bg.display_name for bg in backgrounds],
        "enemies_count": len(enemies),
        "enemies": [enemy.display_name for enemy in enemies],
    }
