"""Character inventory and money management service.

Provides centralized operations for money and inventory management
with consistent validation, atomic operations, and persistence.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ResourceError, ValidationError
from app.models.enums import SkillName
from app.models.gameplay import Character, InventoryItem


# =============================================================================
# Money Operations
# =============================================================================

async def validate_money_bounds(character: Character) -> None:
    """Validate that character money is within valid bounds.

    Args:
        character: Character to validate

    Raises:
        ResourceError: If money is negative
    """
    if character.money < 0:
        raise ResourceError(
            "Money cannot be negative",
            details={"money": character.money},
        )


async def add_money(
    session: AsyncSession,
    character: Character,
    amount: int,
) -> dict:
    """Add money to a character (positive change only).

    Args:
        session: Database session
        character: Character to add money to
        amount: Amount to add (must be positive)

    Returns:
        Dictionary with change details:
        - previous_money: int
        - new_money: int
        - change_amount: int (actual change applied)

    Raises:
        ResourceError: If amount is not positive
    """
    if amount <= 0:
        raise ResourceError(
            "Money add amount must be positive",
            details={"amount": amount},
        )

    previous_money = character.money
    character.money += amount
    await session.flush()
    await validate_money_bounds(character)

    return {
        "previous_money": previous_money,
        "new_money": character.money,
        "change_amount": amount,
    }


async def spend_money(
    session: AsyncSession,
    character: Character,
    amount: int,
) -> dict:
    """Spend money from a character (negative change only).

    Args:
        session: Database session
        character: Character to spend money from
        amount: Amount to spend (must be positive)

    Returns:
        Dictionary with change details:
        - previous_money: int
        - new_money: int
        - change_amount: int (actual change applied, negative)

    Raises:
        ResourceError: If amount is not positive or insufficient funds
    """
    if amount <= 0:
        raise ResourceError(
            "Money spend amount must be positive",
            details={"amount": amount},
        )

    if character.money < amount:
        raise ResourceError(
            "Insufficient funds",
            details={
                "current_money": character.money,
                "required_amount": amount,
            },
        )

    previous_money = character.money
    character.money -= amount
    await session.flush()
    await validate_money_bounds(character)

    return {
        "previous_money": previous_money,
        "new_money": character.money,
        "change_amount": -amount,
    }


async def get_money(character: Character) -> int:
    """Get character's current money.

    Args:
        character: Character to check

    Returns:
        Current money amount
    """
    return character.money


async def can_afford(character: Character, amount: int) -> bool:
    """Check if character can afford an amount.

    Args:
        character: Character to check
        amount: Amount to check

    Returns:
        True if character has enough money, False otherwise
    """
    return character.money >= amount


# =============================================================================
# Inventory Operations
# =============================================================================

async def get_inventory(character: Character) -> list[dict]:
    """Get character's full inventory with details.

    Args:
        character: Character to get inventory for

    Returns:
        List of inventory item dictionaries
    """
    if not character.inventory:
        return []

    inventory = []
    for item in character.inventory:
        inventory.append({
            "id": item.id,
            "item_id": item.item_id,
            "name": item.name,
            "description": item.description,
            "quantity": item.quantity,
            "item_type": item.item_type,
            "value": item.value,
            "is_equipped": item.is_equipped,
            "properties": item.properties,
        })
    return inventory


async def get_inventory_item(
    session: AsyncSession,
    character: Character,
    item_id: str,
) -> InventoryItem | None:
    """Get a specific inventory item by item_id.

    Args:
        session: Database session
        character: Character to search
        item_id: Item identifier to find

    Returns:
        InventoryItem if found, None otherwise
    """
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == character.id,
            InventoryItem.item_id == item_id,
        )
    )
    return result.scalar_one_or_none()


async def get_inventory_item_by_name(
    session: AsyncSession,
    character: Character,
    name: str,
) -> InventoryItem | None:
    """Get a specific inventory item by name (case-insensitive).

    Args:
        session: Database session
        character: Character to search
        name: Item name to find

    Returns:
        InventoryItem if found, None otherwise
    """
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == character.id,
            InventoryItem.name.ilike(name),
        )
    )
    return result.scalar_one_or_none()


async def has_item(
    session: AsyncSession,
    character: Character,
    item_id: str,
    quantity: int = 1,
) -> bool:
    """Check if character has at least the specified quantity of an item.

    Args:
        session: Database session
        character: Character to check
        item_id: Item identifier
        quantity: Required quantity (default 1)

    Returns:
        True if character has enough, False otherwise
    """
    item = await get_inventory_item(session, character, item_id)
    return item is not None and item.quantity >= quantity


async def has_item_by_name(
    session: AsyncSession,
    character: Character,
    name: str,
    quantity: int = 1,
) -> bool:
    """Check if character has at least the specified quantity of an item by name.

    Args:
        session: Database session
        character: Character to check
        name: Item name
        quantity: Required quantity (default 1)

    Returns:
        True if character has enough, False otherwise
    """
    item = await get_inventory_item_by_name(session, character, name)
    return item is not None and item.quantity >= quantity


async def add_item(
    session: AsyncSession,
    character: Character,
    item_name: str,
    quantity: int,
    value: int = 0,
    item_type: str = "misc",
    description: str = "",
    properties: dict | None = None,
    item_id: str | None = None,
) -> InventoryItem:
    """Add item to character inventory (creates new or stacks with existing).

    Args:
        session: Database session
        character: Character to add item to
        item_name: Display name of the item
        quantity: Quantity to add (must be positive)
        value: Item value in gold (default 0)
        item_type: Item category (consumable, equipment, material, misc, etc.)
        description: Item description
        properties: Additional item properties
        item_id: Optional custom item_id (auto-generated from name if not provided)

    Returns:
        The InventoryItem (existing with updated quantity or newly created)

    Raises:
        ResourceError: If quantity is not positive
    """
    if quantity <= 0:
        raise ResourceError(
            "Item quantity must be positive",
            details={"quantity": quantity, "item_name": item_name},
        )

    # Check if item already exists (by item_id or name)
    search_id = item_id or item_name.lower().replace(" ", "_").replace("'", "").replace(",", "")
    existing = await get_inventory_item(session, character, search_id)

    if existing:
        existing.quantity += quantity
        await session.flush()
        return existing

    # Create new item
    new_item = InventoryItem(
        character_id=character.id,
        item_id=search_id,
        name=item_name,
        description=description or f"Acquired during activity.",
        quantity=quantity,
        item_type=item_type,
        value=value,
        is_equipped=False,
        properties=properties or {},
    )
    session.add(new_item)
    await session.flush()
    return new_item


async def remove_item(
    session: AsyncSession,
    character: Character,
    item_id: str,
    quantity: int,
) -> dict:
    """Remove a specific quantity of an item from inventory.

    Args:
        session: Database session
        character: Character to remove item from
        item_id: Item identifier
        quantity: Quantity to remove (must be positive)

    Returns:
        Dictionary with removal details:
        - item_id: str
        - name: str
        - previous_quantity: int
        - new_quantity: int
        - removed_quantity: int
        - fully_removed: bool

    Raises:
        ResourceError: If quantity not positive, item not found, or insufficient quantity
    """
    if quantity <= 0:
        raise ResourceError(
            "Remove quantity must be positive",
            details={"quantity": quantity, "item_id": item_id},
        )

    item = await get_inventory_item(session, character, item_id)
    if not item:
        raise ResourceError(
            "Item not found in inventory",
            details={"item_id": item_id},
        )

    if item.quantity < quantity:
        raise ResourceError(
            "Insufficient item quantity",
            details={
                "item_id": item_id,
                "current_quantity": item.quantity,
                "requested_quantity": quantity,
            },
        )

    previous_quantity = item.quantity
    item.quantity -= quantity
    removed_quantity = quantity
    fully_removed = False

    if item.quantity == 0:
        await session.delete(item)
        fully_removed = True

    await session.flush()

    return {
        "item_id": item.item_id,
        "name": item.name,
        "previous_quantity": previous_quantity,
        "new_quantity": item.quantity if not fully_removed else 0,
        "removed_quantity": removed_quantity,
        "fully_removed": fully_removed,
    }


async def remove_item_by_name(
    session: AsyncSession,
    character: Character,
    name: str,
    quantity: int,
) -> dict:
    """Remove a specific quantity of an item from inventory by name.

    Args:
        session: Database session
        character: Character to remove item from
        name: Item name
        quantity: Quantity to remove (must be positive)

    Returns:
        Dictionary with removal details (same as remove_item)

    Raises:
        ResourceError: If quantity not positive, item not found, or insufficient quantity
    """
    item = await get_inventory_item_by_name(session, character, name)
    if not item:
        raise ResourceError(
            "Item not found in inventory",
            details={"item_name": name},
        )
    return await remove_item(session, character, item.item_id, quantity)


async def consume_item(
    session: AsyncSession,
    character: Character,
    item_id: str,
    quantity: int = 1,
) -> dict:
    """Consume (use and remove) an item from inventory.

    This is an alias for remove_item with semantic meaning of "using" the item.

    Args:
        session: Database session
        character: Character consuming the item
        item_id: Item identifier
        quantity: Quantity to consume (default 1)

    Returns:
        Dictionary with consumption details (same as remove_item)
    """
    return await remove_item(session, character, item_id, quantity)


async def consume_item_by_name(
    session: AsyncSession,
    character: Character,
    name: str,
    quantity: int = 1,
) -> dict:
    """Consume (use and remove) an item from inventory by name.

    Args:
        session: Database session
        character: Character consuming the item
        name: Item name
        quantity: Quantity to consume (default 1)

    Returns:
        Dictionary with consumption details (same as remove_item)
    """
    return await remove_item_by_name(session, character, name, quantity)


async def get_item_count(
    session: AsyncSession,
    character: Character,
    item_id: str,
) -> int:
    """Get the quantity of a specific item in inventory.

    Args:
        session: Database session
        character: Character to check
        item_id: Item identifier

    Returns:
        Quantity of item (0 if not found)
    """
    item = await get_inventory_item(session, character, item_id)
    return item.quantity if item else 0


async def get_total_inventory_value(character: Character) -> int:
    """Calculate total value of all items in inventory.

    Args:
        character: Character to calculate for

    Returns:
        Total value in gold
    """
    if not character.inventory:
        return 0
    return sum(item.value * item.quantity for item in character.inventory)


# =============================================================================
# Treatment-Item Integration
# =============================================================================

# Treatment item mapping (treatment_id -> inventory item_id)
TREATMENT_ITEM_MAP = {
    "bandage": "bandage",
    "healing_herbs": "healing_herbs",
    "antidote": "antidote",
    "splint": "splint",
    "medicine": "medicine",
    "salve": "salve",
    "rest_remedy": "rest_remedy",
}

# Treatment definitions (moved from conditions.py for centralization)
TREATMENTS = {
    "bandage": {
        "name": "Bandage",
        "item_id": "bandage",
        "treats": ["minor_cut", "deep_wound", "burn"],
        "severity_reduction": 1,
        "description": "Clean and wrap the wound.",
    },
    "healing_herbs": {
        "name": "Healing Herbs",
        "item_id": "healing_herbs",
        "treats": ["minor_cut", "minor_illness", "poison"],
        "severity_reduction": 1,
        "description": "Apply herbal poultice.",
    },
    "antidote": {
        "name": "Antidote",
        "item_id": "antidote",
        "treats": ["poison"],
        "severity_reduction": 2,
        "description": "Neutralize the toxin.",
    },
    "splint": {
        "name": "Splint",
        "item_id": "splint",
        "treats": ["broken_bone"],
        "severity_reduction": 1,
        "description": "Immobilize the fracture.",
    },
    "medicine": {
        "name": "Medicine",
        "item_id": "medicine",
        "treats": ["minor_illness", "serious_illness", "concussion"],
        "severity_reduction": 1,
        "description": "Take medicinal tonic.",
    },
    "salve": {
        "name": "Salve",
        "item_id": "salve",
        "treats": ["burn", "frostbite"],
        "severity_reduction": 1,
        "description": "Apply soothing ointment.",
    },
    "rest_remedy": {
        "name": "Rest Remedy",
        "item_id": "rest_remedy",
        "treats": ["exhaustion"],
        "severity_reduction": 2,
        "description": "Special tea for deep recovery.",
    },
}


async def get_treatment_definition(treatment_id: str) -> dict | None:
    """Get treatment definition by ID."""
    return TREATMENTS.get(treatment_id)


async def get_all_treatments() -> dict:
    """Get all treatment definitions."""
    return TREATMENTS.copy()


async def get_treatment_item_id(treatment_id: str) -> str | None:
    """Get the inventory item_id for a treatment."""
    return TREATMENT_ITEM_MAP.get(treatment_id)


async def treat_condition_with_item(
    session: AsyncSession,
    character: Character,
    condition_id: str,
    treatment_id: str,
) -> dict:
    """Treat a condition by consuming a treatment item from inventory.

    This operation is atomic: it consumes the item AND applies the treatment effect.
    If the character doesn't have the item, the treatment fails without side effects.

    Args:
        session: Database session
        character: Character being treated
        condition_id: Condition to treat
        treatment_id: Treatment to use (must match an inventory item)

    Returns:
        Dictionary with treatment result:
        - success: bool
        - removed: bool (whether condition was fully removed)
        - old_severity: int
        - new_severity: int
        - treatment_used: str
        - description: str
        - item_consumed: dict with item details

    Raises:
        ResourceError: If treatment item not in inventory
        ValidationError: If condition not found or treatment invalid
    """
    # Import here to avoid circular dependency
    from app.services.character.conditions import (
        CONDITIONS,
        add_condition,
        remove_condition,
    )

    # Validate condition exists
    if not character.conditions or condition_id not in character.conditions:
        raise ValidationError(
            f"Condition not found: {condition_id}",
            details={"condition_id": condition_id},
        )

    # Validate treatment exists
    treatment = TREATMENTS.get(treatment_id)
    if not treatment:
        raise ValidationError(
            f"Unknown treatment: {treatment_id}",
            details={"treatment_id": treatment_id},
        )

    # Check if treatment can treat this condition
    if condition_id not in treatment["treats"]:
        raise ValidationError(
            f"Treatment {treatment['name']} cannot treat {condition_id}",
            details={"condition_id": condition_id, "treatment_id": treatment_id},
        )

    # Check if character has the treatment item in inventory
    item_id = treatment["item_id"]
    if not await has_item(session, character, item_id, 1):
        raise ResourceError(
            f"You don't have {treatment['name']} in your inventory",
            details={"treatment_id": treatment_id, "item_id": item_id},
        )

    # Consume the item (atomic with treatment effect)
    item_result = await consume_item(session, character, item_id, 1)

    # Apply treatment effect - wrapped to ensure atomicity with item consumption
    # If any exception occurs here, the outer transaction will roll back the item consumption
    try:
        condition = character.conditions[condition_id]
        old_severity = condition["severity"]
        condition["severity"] = max(
            1, condition["severity"] - treatment["severity_reduction"]
        )

        # If severity reaches 1 and duration is low, remove it
        if condition["severity"] <= 1 and condition["duration"] <= 2:
            del character.conditions[condition_id]
            removed = True
            new_severity = 0
        else:
            removed = False
            new_severity = condition["severity"]

        # Mark conditions as modified for JSON column
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(character, "conditions")
        await session.flush()
    except Exception:
        # Re-raise to trigger outer transaction rollback (which will undo item consumption)
        raise

    return {
        "success": True,
        "removed": removed,
        "old_severity": old_severity,
        "new_severity": new_severity,
        "treatment_used": treatment["name"],
        "description": treatment["description"],
        "item_consumed": item_result,
    }


async def get_available_treatments_for_condition(
    session: AsyncSession,
    character: Character,
    condition_id: str,
) -> list[dict]:
    """Get list of treatments that can treat a condition and are in inventory.

    Args:
        session: Database session
        character: Character to check inventory for
        condition_id: Condition to find treatments for

    Returns:
        List of available treatment dictionaries with inventory status
    """
    available = []
    for treatment_id, treatment in TREATMENTS.items():
        if condition_id in treatment["treats"]:
            has_item = await has_item(session, character, treatment["item_id"], 1)
            available.append({
                "treatment_id": treatment_id,
                "name": treatment["name"],
                "description": treatment["description"],
                "severity_reduction": treatment["severity_reduction"],
                "in_inventory": has_item,
            })
    return available


# =============================================================================
# Validation Helpers
# =============================================================================

async def validate_character_inventory(character: Character) -> None:
    """Validate all character inventory items are in valid state.

    Args:
        character: Character to validate

    Raises:
        ResourceError: If any inventory item is invalid
    """
    if not character.inventory:
        return

    for item in character.inventory:
        if item.quantity <= 0:
            raise ResourceError(
                "Inventory item quantity must be positive",
                details={"item_id": item.item_id, "quantity": item.quantity},
            )
        if item.value < 0:
            raise ResourceError(
                "Inventory item value cannot be negative",
                details={"item_id": item.item_id, "value": item.value},
            )