"""
Migration: 011-source-constitutional-commissions
Description: Import constitutional commissions and government bodies with 4-depth prefixes
Author: Kushal KC
Date: 2026-03-22
"""

from nes.core.models.entity import EntitySubType, EntityType
from nes.core.models.version import Author
from nes.core.utils.slug_helper import text_to_slug
from nes.services.migration.context import MigrationContext

# Migration metadata
AUTHOR = "Kushal KC"
DATE = "2026-03-22"
DESCRIPTION = "Import constitutional commissions and government bodies with 4-depth prefixes"
CHANGE_DESCRIPTION = "Initial sourcing of constitutional commissions"


async def migrate(context: MigrationContext) -> None:
    """
    Import constitutional commissions and government bodies.

    This migration introduces 4-depth entity prefixes for better organization:
    - organization/government/commission/federal (9 entities)
    - organization/government/commission/province (14 entities: 7 NHRC + 7 PSC)
    - organization/government/commission/regional (8 entities: CIAA regional offices)
    - organization/government/commission/district (77 entities: District Election Offices)

    Data source: Constitutional commissions data compiled from official sources
    """
    context.log("Migration started: Importing constitutional commissions")

    # Create author
    author = Author(slug=text_to_slug(AUTHOR), name=AUTHOR)
    await context.db.put_author(author)
    author_id = author.id
    context.log(f"Created author: {author.name} ({author_id})")

    # Load entity data
    entities = context.read_json("source/constitutional_commissions.json")
    context.log(f"Loaded {len(entities)} entities from constitutional_commissions.json")

    # Count by prefix
    prefix_counts = {
        "organization/government/commission/federal": 0,
        "organization/government/commission/province": 0,
        "organization/government/commission/regional": 0,
        "organization/government/commission/district": 0,
    }

    count = 0
    for entity_data in entities:
        # Extract entity_prefix from the data
        entity_prefix = entity_data.get("entity_prefix")
        
        # Remove fields that shouldn't be in entity_data for creation
        entity_data_clean = {k: v for k, v in entity_data.items() 
                            if k not in ["entity_prefix", "type", "sub_type", "created_at", "version_summary"]}
        
        # Create entity using the publication service
        entity = await context.publication.create_entity(
            entity_type=EntityType.ORGANIZATION,
            entity_subtype=EntitySubType.GOVERNMENT_BODY,
            entity_data=entity_data_clean,
            author_id=author_id,
            change_description=CHANGE_DESCRIPTION,
            entity_prefix=entity_prefix,
        )
        
        # Count by prefix
        if entity_prefix in prefix_counts:
            prefix_counts[entity_prefix] += 1
        
        context.log(f"Created entity {entity.id} with prefix {entity_prefix}")
        count += 1

    context.log(f"\nCreated {count} constitutional commission entities")
    context.log("\nPrefix distribution:")
    for prefix, prefix_count in prefix_counts.items():
        context.log(f"  {prefix}: {prefix_count}")

    # Verify
    entities_in_db = await context.db.list_entities(
        limit=200, entity_type="organization", sub_type="government_body"
    )
    context.log(f"\nVerified: {len(entities_in_db)} government_body entities in database")

    context.log("Migration completed successfully")
