"""
Migration: 011-source-federal-commissions
Description: Import Nepal's constitutional commissions (7 Provincial PSCs + 9 single-office commissions)
Author: Kushal KC
Date: 2026-03-06
"""

from typing import Any, Dict, List, Optional

from nes.core.models import (
    Address,
    Contact,
    LangText,
    LangTextValue,
    Name,
    NameParts,
)
from nes.core.models.base import ContactType, NameKind, ProvenanceMethod
from nes.core.models.entity import EntitySubType, EntityType
from nes.core.models.version import Author
from nes.core.utils.slug_helper import text_to_slug
from nes.services.migration.context import MigrationContext
from nes.services.scraping.normalization import NameExtractor

# Migration metadata
AUTHOR = "Kushal KC"
DATE = "2026-03-06"
DESCRIPTION = "Import Nepal's constitutional commissions (7 Provincial PSCs + 9 single-office commissions)"
CHANGE_DESCRIPTION = "Import constitutional commissions"

name_extractor = NameExtractor()


async def migrate(context: MigrationContext) -> None:
    """
    Import Nepal's constitutional commissions:
    - 7 Provincial Public Service Commissions
    - 9 Single-office constitutional commissions

    Data source: Official commission websites and collegenp.com
    """
    context.log("Migration started: Importing constitutional commissions")

    # Create author
    author = Author(slug=text_to_slug(AUTHOR), name=AUTHOR)
    await context.db.put_author(author)
    author_id = author.id
    context.log(f"Created author: {author.name} ({author_id})")

    # Load constitutional commissions data
    commissions_data = context.read_json("source/constitutional_commissions.json")
    context.log(f"Loaded {len(commissions_data)} constitutional commissions from source data")

    # Build location lookups
    context.log("Building location lookups...")
    location_lookup = await _build_location_lookups(context)
    context.log(f"Built location lookups: {len(location_lookup)} entries")

    # STAGE 1: Build commission data structures
    context.log("Stage 1: Building commission data structures...")
    entities_to_create = []

    for office in commissions_data:
        slug = office["slug"]
        
        # Build names
        name_en = name_extractor.standardize_name(office["name_en"])
        name_ne = name_extractor.standardize_name(office["name_ne"])
        
        names = [
            Name(
                kind=NameKind.PRIMARY,
                en=NameParts(full=name_en),
                ne=NameParts(full=name_ne),
            ).model_dump()
        ]

        # Build short description
        short_description = LangText(
            en=LangTextValue(value=office['short_description_en'], provenance=ProvenanceMethod.IMPORTED),
            ne=LangTextValue(value=office['short_description_ne'], provenance=ProvenanceMethod.IMPORTED),
        )
        
        # Build description (longer, detailed)
        description = LangText(
            en=LangTextValue(value=office['description_en'], provenance=ProvenanceMethod.IMPORTED),
            ne=LangTextValue(value=office['description_ne'], provenance=ProvenanceMethod.IMPORTED),
        )
        
        # Find location ID (ward > municipality > province)
        location_id = _find_location_id(
            location_lookup=location_lookup,
            municipality_en=office.get("municipality_en"),
            ward_number=office.get("ward_number"),
            province_en=office.get("province_en"),
            context=context
        )
        
        # Build address
        address_en = office.get('address_en', '')
        address_ne = office.get('address_ne', '')
        
        address = None
        if address_en or address_ne:
            address = Address(
                location_id=location_id,
                description=None,
                description2=LangText(
                    en=LangTextValue(value=address_en, provenance=ProvenanceMethod.IMPORTED) if address_en else None,
                    ne=LangTextValue(value=address_ne, provenance=ProvenanceMethod.IMPORTED) if address_ne else None,
                ),
            )

        # Build contacts (phones, email, website)
        contacts = []
        
        # Add phone contacts
        for phone in office.get("phones", []):
            if phone:
                contacts.append(Contact(type=ContactType.PHONE, value=phone))
        
        # Add email contact
        if office.get("email"):
            contacts.append(Contact(type=ContactType.EMAIL, value=office["email"]))
        
        # Add website contact
        if office.get("website"):
            contacts.append(Contact(type=ContactType.URL, value=office["website"]))

        # Build tags - using same tags for all commissions for now
        tags = ["constitutional-body"]

        # Build attributes
        attributes = {}
        if office.get("established"):
            attributes["established"] = office["established"]

        # Create entity data structure
        entity_data = dict(
            slug=slug,
            names=names,
            address=address.model_dump() if address else None,
            contacts=contacts if contacts else None,
            short_description=short_description.model_dump(),
            description=description.model_dump(),
            tags=tags,
            attributes=attributes if attributes else None,
            government_type="provincial",
        )

        entities_to_create.append(
            {"data": entity_data, "name_en": name_en, "name_ne": name_ne}
        )

    context.log(f"Stage 1 complete: Prepared {len(entities_to_create)} commissions")

    # STAGE 2: Check for duplicates
    context.log("Stage 2: Checking for duplicates...")
    existing_entities = await context.db.list_entities(
        limit=10000, entity_type="organization", sub_type="government_body"
    )
    
    # Build lookup maps for existing entities
    existing_slugs = {entity.slug: entity for entity in existing_entities}
    existing_names_en = {}
    existing_names_ne = {}
    
    for entity in existing_entities:
        primary_name = next((n for n in entity.names if n.kind.value == "PRIMARY"), None)
        if primary_name:
            if primary_name.en and primary_name.en.full:
                name_en_normalized = primary_name.en.full.lower().strip()
                existing_names_en[name_en_normalized] = entity
            if primary_name.ne and primary_name.ne.full:
                name_ne_normalized = primary_name.ne.full.strip()
                existing_names_ne[name_ne_normalized] = entity

    context.log(f"Found {len(existing_entities)} existing government_body entities in database")

    # Check for duplicates within migration data
    slug_counts = {}
    migration_duplicates = []
    
    for entity in entities_to_create:
        slug = entity["data"]["slug"]
        
        if slug in slug_counts:
            slug_counts[slug] += 1
            migration_duplicates.append(
                f"Duplicate slug '{slug}' in migration data for {entity['name_en']}"
            )
        else:
            slug_counts[slug] = 1

    if migration_duplicates:
        context.log("DUPLICATES IN MIGRATION DATA DETECTED:")
        for dup in migration_duplicates:
            context.log(f"  - {dup}")
        raise ValueError(f"Found {len(migration_duplicates)} duplicates in migration data. Please clean source data first.")

    # Separate entities into new and existing
    entities_to_skip = []
    entities_to_insert = []
    
    for entity in entities_to_create:
        slug = entity["data"]["slug"]
        name_en_normalized = entity["name_en"].lower().strip()
        name_ne_normalized = entity["name_ne"].strip()
        
        # Check for duplicates by slug
        if slug in existing_slugs:
            existing = existing_slugs[slug]
            entities_to_skip.append({
                "entity": entity,
                "reason": "slug",
                "existing_id": existing.id
            })
            context.log(f"Skipping duplicate (by slug): {entity['name_en']} -> existing: {existing.id}")
        # Check for duplicates by English name
        elif name_en_normalized in existing_names_en:
            existing = existing_names_en[name_en_normalized]
            entities_to_skip.append({
                "entity": entity,
                "reason": "name_en",
                "existing_id": existing.id
            })
            context.log(f"Skipping duplicate (by English name): {entity['name_en']} -> existing: {existing.id}")
        # Check for duplicates by Nepali name
        elif name_ne_normalized in existing_names_ne:
            existing = existing_names_ne[name_ne_normalized]
            entities_to_skip.append({
                "entity": entity,
                "reason": "name_ne",
                "existing_id": existing.id
            })
            context.log(f"Skipping duplicate (by Nepali name): {entity['name_ne']} -> existing: {existing.id}")
        else:
            entities_to_insert.append(entity)

    context.log(
        f"Stage 2 complete: {len(entities_to_insert)} new commissions to create, {len(entities_to_skip)} already exist"
    )

    # STAGE 3: Create entities in database
    context.log("Stage 3: Creating entities in database...")
    created_count = 0

    for entity in entities_to_insert:
        psc_entity = await context.publication.create_entity(
            entity_type=EntityType.ORGANIZATION,
            entity_subtype=EntitySubType.GOVERNMENT_BODY,
            entity_data=entity["data"],
            author_id=author_id,
            change_description=CHANGE_DESCRIPTION,
        )
        context.log(
            f"Created commission {psc_entity.id}: {entity['name_en']} ({entity['name_ne']})"
        )
        created_count += 1

    context.log(f"Stage 3 complete: Created {created_count} commissions, skipped {len(entities_to_skip)} duplicates")

    # Log details of skipped entities
    if entities_to_skip:
        context.log("\nSkipped entities (already exist in database):")
        for skipped in entities_to_skip:
            context.log(f"  - {skipped['entity']['name_en']} (reason: {skipped['reason']}, existing ID: {skipped['existing_id']})")

    # Final verification
    all_govt_bodies = await context.db.list_entities(
        limit=10000, entity_type="organization", sub_type="government_body"
    )
    context.log(
        f"Final verification: {len(all_govt_bodies)} total government_body entities in database"
    )

    context.log("Migration completed successfully")


async def _build_location_lookups(context: MigrationContext) -> Dict[str, Any]:
    """Build lookup dictionary for locations (wards, municipalities, provinces)."""
    locations = await context.search.search_entities(
        entity_type="location", limit=10_000
    )
    
    location_lookup = {}
    
    for loc in locations:
        st = loc.sub_type.value if loc.sub_type else None
        for nm in loc.names:
            if nm.en and nm.en.full:
                key = nm.en.full.strip().lower()
                location_lookup[key] = loc
            if nm.ne and nm.ne.full:
                key = nm.ne.full.strip().lower()
                location_lookup[key] = loc
    
    return location_lookup


def _find_location_id(
    location_lookup: Dict[str, Any],
    municipality_en: Optional[str],
    ward_number: Optional[int],
    province_en: Optional[str],
    context: MigrationContext
) -> Optional[str]:
    """
    Find location ID with fallback strategy: ward > municipality > province.
    
    Ward names follow the pattern: "{municipality-slug} - Ward {number}"
    """
    # Try ward first if ward_number is provided
    if ward_number and municipality_en:
        # Use the full municipality name as it appears in the database
        ward_name = f"{municipality_en} - Ward {ward_number}"
        key = ward_name.strip().lower()
        
        if key in location_lookup:
            loc_id = location_lookup[key].id
            context.log(f"  Found ward location: {ward_name} -> {loc_id}")
            return loc_id
        else:
            context.log(f"  Ward not found: {ward_name}, falling back to municipality")
    
    # Try municipality
    if municipality_en:
        key = municipality_en.strip().lower()
        if key in location_lookup:
            loc_id = location_lookup[key].id
            context.log(f"  Found municipality location: {municipality_en} -> {loc_id}")
            return loc_id
        else:
            context.log(f"  Municipality not found: {municipality_en}, falling back to province")
    
    # Try province as last resort
    if province_en:
        key = province_en.strip().lower()
        if key in location_lookup:
            loc_id = location_lookup[key].id
            context.log(f"  Found province location: {province_en} -> {loc_id}")
            return loc_id
        else:
            context.log(f"  Province not found: {province_en}")
    
    context.log("  No location found, location_id will be None")
    return None
