"""
Migration: 009-party-election-symbols
Description: Add election symbol pictures to political parties
Author: Damodar Dahal
Date: 2026-01-08
"""

from nes.core.models import EntityPicture, EntityPictureType
from nes.core.models.entity import EntitySubType, EntityType
from nes.services.migration.context import MigrationContext

# Migration metadata
AUTHOR = "Damodar Dahal"
DATE = "2026-01-08"
DESCRIPTION = "Add election symbol pictures to political parties"
CHANGE_DESCRIPTION = "Add 2082 election symbol pictures"


async def migrate(context: MigrationContext) -> None:
    """
    Add election symbol pictures to political parties.

    This migration:
    1. Gets all political parties in the system
    2. Checks if their slug exists in existing-symbols.txt
    3. If it exists, adds a picture URL for the 2082 election symbol
    """

    context.log(
        "Migration started: Adding election symbol pictures to political parties"
    )

    # Use existing author (should already exist)
    author_id = "author:damodar-dahal"
    context.log(f"Using existing author: ({author_id})")

    # Load existing symbols from file
    with open(context.migration_dir / "existing-symbols.txt", "r") as f:
        existing_symbols_content = f.read()
    existing_symbols = set()
    for line in existing_symbols_content.strip().split("\n"):
        if line.strip() and line.endswith(".png"):
            # Remove .png extension to get the slug
            slug = line.strip()[:-4]  # Remove last 4 characters (.png)
            existing_symbols.add(slug)

    context.log(f"Loaded {len(existing_symbols)} existing symbol slugs")

    # Get all political parties
    parties = await context.db.list_entities(
        entity_type=EntityType.ORGANIZATION,
        sub_type=EntitySubType.POLITICAL_PARTY,
        limit=1000,
    )

    context.log(f"Found {len(parties)} political parties in the system")

    # Process each party
    updated_count = 0
    skipped_count = 0

    for party in parties:
        party_slug = party.slug

        # Check if this party's slug exists in the symbols file
        if party_slug in existing_symbols:
            # Build the picture URL
            picture_url = f"https://assets.nes.jawafdehi.org/assets/images/2082-election-symbols/{party_slug}.png"

            # Create the picture object
            picture = EntityPicture(
                type=EntityPictureType.THUMB,
                url=picture_url,
                description="2082 Election Symbol. Source: Nepal Election Commission",
            )

            # Update the party entity directly
            party.pictures = [picture]

            await context.publication.update_entity(
                entity=party,
                author_id=author_id,
                change_description=CHANGE_DESCRIPTION,
            )

            context.log(f"Added symbol picture to party: {party_slug}")
            updated_count += 1
        else:
            context.log(f"No symbol found for party: {party_slug}")
            skipped_count += 1

    context.log(
        f"Migration completed: Updated {updated_count} parties, skipped {skipped_count} parties"
    )
