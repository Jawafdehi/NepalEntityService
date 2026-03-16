"""Validation functions for identifiers in nes."""

import re

from ..constraints import MAX_SLUG_LENGTH, MIN_SLUG_LENGTH, SLUG_PATTERN
from .builders import (
    break_author_id,
    break_entity_id,
    break_relationship_id,
    break_version_id,
)


def is_valid_entity_id(entity_id: str) -> bool:
    """Validate if a string is a valid entity ID format.

    Args:
        entity_id: The entity ID string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        validate_entity_id(entity_id)
        return True
    except ValueError:
        return False


def validate_entity_id(entity_id: str) -> str:
    """Validate entity ID and return it if valid, raise ValueError if not.

    Validates:
    - Format: must start with "entity:" and have 1-MAX_PREFIX_DEPTH prefix segments + slug
    - Prefix: must be present in ALLOWED_ENTITY_PREFIXES
    - Slug: must match SLUG_PATTERN and length constraints

    Args:
        entity_id: The entity ID string to validate

    Returns:
        The validated entity ID

    Raises:
        ValueError: If the entity ID format or prefix is invalid
    """
    from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

    try:
        components = break_entity_id(entity_id)
    except ValueError as e:
        raise ValueError(f"Invalid entity ID format: {entity_id}") from e

    # Validate prefix against the canonical registry
    if components.prefix not in ALLOWED_ENTITY_PREFIXES:
        raise ValueError(
            f"Entity prefix '{components.prefix}' is not allowed. "
            f"Add it to ALLOWED_ENTITY_PREFIXES in nes/core/models/entity_type_map.py."
        )

    # Validate slug
    if len(components.slug) < MIN_SLUG_LENGTH or len(components.slug) > MAX_SLUG_LENGTH:
        raise ValueError(f"Entity slug length invalid: {components.slug}")
    if not re.match(SLUG_PATTERN, components.slug):
        raise ValueError(f"Invalid entity slug format: {components.slug}")

    return entity_id


def is_valid_relationship_id(relationship_id: str) -> bool:
    """Validate if a string is a valid relationship ID format."""
    try:
        validate_relationship_id(relationship_id)
        return True
    except ValueError:
        return False


def validate_relationship_id(relationship_id: str) -> str:
    """Validate relationship ID and return it if valid, raise ValueError if not."""
    try:
        components = break_relationship_id(relationship_id)
    except ValueError as e:
        raise ValueError(f"Invalid relationship ID format: {relationship_id}") from e

    # Validate that source and target are valid entity IDs
    validate_entity_id(components.source)
    validate_entity_id(components.target)

    return relationship_id


def is_valid_version_id(version_id: str) -> bool:
    """Validate if a string is a valid version ID format."""
    try:
        validate_version_id(version_id)
        return True
    except ValueError:
        return False


def validate_version_id(version_id: str) -> str:
    """Validate version ID and return it if valid, raise ValueError if not."""
    try:
        components = break_version_id(version_id)
    except ValueError as e:
        # Re-raise the original error to preserve specific error messages
        raise e

    # Validate the underlying entity or relationship ID
    if components.entity_or_relationship_id.startswith("entity:"):
        validate_entity_id(components.entity_or_relationship_id)
    elif components.entity_or_relationship_id.startswith("relationship:"):
        validate_relationship_id(components.entity_or_relationship_id)

    return version_id


def is_valid_author_id(author_id: str) -> bool:
    """Validate if a string is a valid author ID format."""
    try:
        validate_author_id(author_id)
        return True
    except ValueError:
        return False


def validate_author_id(author_id: str) -> str:
    """Validate author ID and return it if valid, raise ValueError if not."""
    try:
        components = break_author_id(author_id)
    except ValueError as e:
        raise ValueError(f"Invalid author ID format: {author_id}") from e

    # Validate slug follows same pattern as entity slugs
    if len(components.slug) < MIN_SLUG_LENGTH or len(components.slug) > MAX_SLUG_LENGTH:
        raise ValueError(f"Author slug length invalid: {components.slug}")
    if not re.match(SLUG_PATTERN, components.slug):
        raise ValueError(f"Invalid author slug format: {components.slug}")

    return author_id
