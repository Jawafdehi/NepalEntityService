"""
Utility functions for working with NES entities.

TODO: This module contains logic that belongs in the NES package itself.
Once the NES package exposes these utilities, we should remove this file
and import from NES directly to avoid code duplication and ensure we stay
in sync with NES's entity model evolution.
"""

from typing import Any, Dict

from nes.core.models.entity import Entity
from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES, ENTITY_PREFIX_MAP


def entity_from_dict(data: Dict[str, Any]) -> Entity:
    """Convert a dictionary to an Entity instance.

    Determines the correct entity subclass based on the 'entity_prefix' field
    in the data, then validates and constructs the appropriate instance.

    This is a local copy of the logic from nes.database.file_database.FileDatabase._entity_from_dict
    to avoid circular dependencies and ensure the validation logic stays in sync with NES.

    TODO: This function should be moved to the NES package as a public utility.
    Once available in NES, import from there instead of maintaining this copy.

    Args:
        data: Dictionary representation of an entity. Must include 'entity_prefix' field.

    Returns:
        Entity instance of the appropriate subclass (Person, Organization, etc.)

    Raises:
        ValueError: If entity_prefix is invalid or missing
        pydantic.ValidationError: If the data fails validation for the entity type
    """
    if "entity_prefix" not in data:
        raise ValueError("Entity must have an 'entity_prefix' field")

    entity_prefix = data["entity_prefix"]

    if entity_prefix is None:
        raise ValueError("Entity 'entity_prefix' field cannot be None")

    # Look up the entity class from the prefix map
    entity_class = ENTITY_PREFIX_MAP.get(entity_prefix)

    if entity_class is None:
        # If exact match not found, try matching just the first segment (base type)
        prefix_parts = entity_prefix.split("/")
        base_type = prefix_parts[0]
        entity_class = ENTITY_PREFIX_MAP.get(base_type)

        if entity_class is None:
            raise ValueError(
                f"Unknown entity_prefix: '{entity_prefix}'. "
                f"Supported prefixes: {', '.join(sorted(ALLOWED_ENTITY_PREFIXES))}"
            )

    return entity_class.model_validate(data)
