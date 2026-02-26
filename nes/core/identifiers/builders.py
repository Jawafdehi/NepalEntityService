"""ID builder functions for nes."""

from typing import NamedTuple

from nes.core.constraints import MAX_PREFIX_DEPTH


class EntityIdComponents(NamedTuple):
    """Components of a parsed entity ID.

    Fields:
        prefix: The full slash-joined classification path, e.g. "organization/nepal_govt/moha"
        slug:   The unique slug, e.g. "department-of-immigration"

    Backward-compat properties:
        type:    First segment of prefix (e.g. "organization")
        subtype: Second segment of prefix, or None if prefix is 1 segment
    """

    prefix: str
    slug: str

    @property
    def type(self) -> str:
        """First segment of entity_prefix — backward compat."""
        return self.prefix.split("/")[0]

    @property
    def subtype(self) -> str | None:
        """Second segment of entity_prefix, or None — backward compat."""
        parts = self.prefix.split("/")
        return parts[1] if len(parts) >= 2 else None


class RelationshipIdComponents(NamedTuple):
    source: str
    target: str
    type: str


class AuthorIdComponents(NamedTuple):
    slug: str


class VersionIdComponents(NamedTuple):
    entity_or_relationship_id: str
    version_number: int


def build_entity_id_from_prefix(prefix: str, slug: str) -> str:
    """Build entity ID from an entity_prefix and slug.

    This is the primary builder for entity IDs. The prefix is a slash-joined
    classification path of 1 to MAX_PREFIX_DEPTH segments.

    Examples:
        >>> build_entity_id_from_prefix("person", "rabi-lamichhane")
        "entity:person/rabi-lamichhane"
        >>> build_entity_id_from_prefix("organization/political_party", "national-independent-party")
        "entity:organization/political_party/national-independent-party"
        >>> build_entity_id_from_prefix("organization/nepal_govt/moha", "department-of-immigration")
        "entity:organization/nepal_govt/moha/department-of-immigration"
    """
    return f"entity:{prefix}/{slug}"


def build_entity_id(type: str, subtype: str | None, slug: str) -> str:
    """Build entity ID from type, subtype, and slug.

    Deprecated: use build_entity_id_from_prefix() instead.

    Examples:
        >>> build_entity_id("person", None, "ram-chandra-poudel")
        "entity:person/ram-chandra-poudel"
        >>> build_entity_id("organization", "political_party", "nepali-congress")
        "entity:organization/political_party/nepali-congress"
    """
    prefix = type if subtype is None else f"{type}/{subtype}"
    return build_entity_id_from_prefix(prefix, slug)


def break_entity_id(entity_id: str) -> EntityIdComponents:
    """Break entity ID into EntityIdComponents(prefix, slug).

    Supports entity_prefix of 1 to MAX_PREFIX_DEPTH segments.

    Examples:
        >>> break_entity_id("entity:person/rabi-lamichhane")
        EntityIdComponents(prefix='person', slug='rabi-lamichhane')
        >>> break_entity_id("entity:organization/political_party/nepali-congress")
        EntityIdComponents(prefix='organization/political_party', slug='nepali-congress')
        >>> break_entity_id("entity:organization/nepal_govt/moha/department-of-immigration")
        EntityIdComponents(prefix='organization/nepal_govt/moha', slug='department-of-immigration')
    """
    if not entity_id.startswith("entity:"):
        raise ValueError("Invalid entity ID format")

    parts = entity_id[7:].split("/")  # Remove "entity:" prefix

    # Need at least 2 parts (1-segment prefix + slug)
    # At most MAX_PREFIX_DEPTH + 1 parts (N-segment prefix + slug)
    if len(parts) < 2 or len(parts) > MAX_PREFIX_DEPTH + 1:
        raise ValueError(
            f"Invalid entity ID format: prefix depth must be 1–{MAX_PREFIX_DEPTH}"
        )

    slug = parts[-1]
    prefix = "/".join(parts[:-1])
    return EntityIdComponents(prefix=prefix, slug=slug)


def build_relationship_id(source: str, target: str, type: str) -> str:
    """Build relationship ID in format: relationship:<source>:<target>:<type>.

    Example:
        >>> build_relationship_id("entity:person/ram-chandra-poudel", "entity:organization/political_party/nepali-congress", "MEMBER_OF")
        "relationship:person/ram-chandra-poudel:organization/political_party/nepali-congress:MEMBER_OF"
    """
    # Extract ID parts without "entity:" prefix
    source_part = (
        source.replace("entity:", "") if source.startswith("entity:") else source
    )
    target_part = (
        target.replace("entity:", "") if target.startswith("entity:") else target
    )
    return f"relationship:{source_part}:{target_part}:{type}"


def break_relationship_id(relationship_id: str) -> RelationshipIdComponents:
    """Break relationship ID into components: RelationshipIdComponents(source, target, type).

    Example:
        >>> break_relationship_id("relationship:person/ram-chandra-poudel:organization/political_party/nepali-congress:MEMBER_OF")
        RelationshipIdComponents(source='entity:person/ram-chandra-poudel', target='entity:organization/political_party/nepali-congress', type='MEMBER_OF')
    """
    if not relationship_id.startswith("relationship:"):
        raise ValueError("Invalid relationship ID format")

    # Remove "relationship:" prefix
    remaining = relationship_id[13:]

    # Split by ':' to get source, target, type
    parts = remaining.split(":")
    if len(parts) != 3:
        raise ValueError("Invalid relationship ID format")

    source_part, target_part, rel_type = parts

    # Convert back to proper entity IDs
    source = f"entity:{source_part}"
    target = f"entity:{target_part}"

    return RelationshipIdComponents(source=source, target=target, type=rel_type)


def build_author_id(slug: str) -> str:
    """Build author ID in format: author:<slug>.

    Example:
        >>> build_author_id("csv-importer")
        "author:csv-importer"
    """
    return f"author:{slug}"


def break_author_id(author_id: str) -> AuthorIdComponents:
    """Break author ID into components: AuthorIdComponents(slug).

    Example:
        >>> break_author_id("author:csv-importer")
        AuthorIdComponents(slug='csv-importer')
    """
    if not author_id.startswith("author:"):
        raise ValueError("Invalid author ID format")

    slug = author_id[7:]  # Remove "author:" prefix
    return AuthorIdComponents(slug=slug)


def build_version_id(entity_or_relationship_id: str, version_number: int) -> str:
    """Build version ID in format: version:<entity_or_relationship_id>:<version_number>.

    Example:
        >>> build_version_id("entity:person/ram-chandra-poudel", 1)
        "version:entity:person/ram-chandra-poudel:1"
        >>> build_version_id("relationship:person/ram-chandra-poudel:organization/political_party/nepali-congress:MEMBER_OF", 2)
        "version:relationship:person/ram-chandra-poudel:organization/political_party/nepali-congress:MEMBER_OF:2"
    """
    return f"version:{entity_or_relationship_id}:{version_number}"


def break_version_id(version_id: str) -> VersionIdComponents:
    """Break version ID into components: VersionIdComponents(entity_or_relationship_id, version_number).

    Example:
        >>> break_version_id("version:entity:person/ram-chandra-poudel:1")
        VersionIdComponents(entity_or_relationship_id='entity:person/ram-chandra-poudel', version_number=1)
    """
    if not version_id.startswith("version:"):
        raise ValueError("Invalid version ID format")

    # Remove "version:" prefix
    remaining = version_id[8:]

    # Check if it's an entity or relationship ID
    if remaining.startswith("entity:"):
        # For entity IDs: version:entity:type/subtype/slug:version_number
        # Split after "entity:" to separate the entity part from version
        entity_part = remaining[7:]  # Remove "entity:" prefix
        parts = entity_part.rsplit(":", 1)
        if len(parts) != 2:
            raise ValueError("Invalid version ID format")
        entity_core, version_str = parts
        entity_id = f"entity:{entity_core}"
    elif remaining.startswith("relationship:"):
        # For relationship IDs: version:relationship:source:target:type:version_number
        # Need to find the last colon that separates the version number
        parts = remaining.rsplit(":", 1)
        if len(parts) != 2:
            raise ValueError("Invalid version ID format")
        relationship_id, version_str = parts
        entity_id = relationship_id
    else:
        raise ValueError("Version ID must contain entity or relationship ID")

    try:
        version_number = int(version_str)
    except ValueError:
        raise ValueError("Invalid version number format")

    return VersionIdComponents(
        entity_or_relationship_id=entity_id, version_number=version_number
    )
