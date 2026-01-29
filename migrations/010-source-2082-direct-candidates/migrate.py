"""
Migration: 010-source-2082-direct-candidates
Description: Create new political parties and fix existing party names for 2082 election
Author: Damodar Dahal
Date: 2026-01-27
"""

import csv
from datetime import date

from nepali_date_utils import converter

from nes.core.models import (
    Address,
    Attribution,
    EntityPicture,
    EntityPictureType,
    ExternalIdentifier,
    LangText,
    LangTextValue,
    Name,
    NameParts,
    PartySymbol,
)
from nes.core.models.base import NameKind
from nes.core.models.entity import EntitySubType, EntityType
from nes.core.models.person import (
    Candidacy,
    Education,
    ElectionPosition,
    ElectionSymbol,
    ElectionType,
    ElectoralDetails,
    Gender,
    PersonDetails,
    Position,
)
from nes.core.utils.devanagari import transliterate_to_roman
from nes.core.utils.slug_helper import text_to_slug
from nes.services.migration.context import MigrationContext
from nes.services.scraping.normalization import NameExtractor

# Migration metadata
AUTHOR = "Damodar Dahal"
DATE = "2026-01-27"
DESCRIPTION = (
    "Create new political parties and fix existing party names for 2082 election"
)
CHANGE_DESCRIPTION = "2082 Election - Political Party Updates"

AUTHOR_ID = "author:damodar-dahal"

name_extractor = NameExtractor()


def convert_nepali_date(date_str: str) -> date:
    """Convert Nepali date to date object."""
    date_roman = transliterate_to_roman(date_str)
    y, m, d = date_roman.split("/")
    date_bs = f"{y.zfill(4)}/{m.zfill(2)}/{d.zfill(2)}"
    date_ad = converter.bs_to_ad(date_bs)
    y, m, d = date_ad.split("/")
    return date(int(y), int(m), int(d))


reg_no_external_identifier = LangText(
    en=LangTextValue(
        value="Election Commission Registration Number (2082)", provenance="human"
    ),
    ne=LangTextValue(value="निर्वाचन आयोग दर्ता नं.", provenance="human"),
)


async def fix_political_parties(context: MigrationContext) -> None:
    """
    Create new political parties and fix existing party names.

    This function:
    1. Creates three new political parties for 2082 election
    2. Updates existing parties with corrected names

    Uses AUTHOR_ID for all updates (no collision detection).
    """
    context.log("Starting fix_political_parties...")

    # Load party updates data
    party_updates = context.read_json("data/party-updates.json")

    # STAGE 1: Create new political parties
    context.log("Stage 1: Creating new political parties...")
    new_parties = party_updates["new_parties"]
    created_count = 0

    for party_data in new_parties:
        # Build identifiers
        identifiers = [
            ExternalIdentifier(
                scheme="other",
                name=reg_no_external_identifier,
                value=party_data["registration_number"],
            )
        ]

        # Build address
        address = Address(
            description2=LangText(
                en=LangTextValue(
                    value=party_data["address_english"],
                    provenance="translation_service",
                ),
                ne=LangTextValue(
                    value=party_data["address_nepali"], provenance="imported"
                ),
            )
        )

        # Build party_chief
        party_chief = LangText(
            en=LangTextValue(
                value=party_data["chief_english"], provenance="translation_service"
            ),
            ne=LangTextValue(value=party_data["chief"], provenance="imported"),
        )

        # Build registration_date
        registration_date = convert_nepali_date(party_data["registration_date"])

        # Build symbol
        symbol = PartySymbol(
            name=LangText(
                en=LangTextValue(
                    value=party_data["symbol_name_english"],
                    provenance="translation_service",
                ),
                ne=LangTextValue(
                    value=party_data["symbol_name_nepali"], provenance="imported"
                ),
            )
        )

        # Build names
        names = [
            Name(
                kind=NameKind.PRIMARY,
                en=NameParts(full=party_data["english_name"]),
                ne=NameParts(full=party_data["nepali_name"]),
            ).model_dump()
        ]

        # Build picture (logo)
        picture_url = f"https://assets.nes.newnepal.org/assets/images/2082-election-symbols/{party_data['slug']}.png"
        picture = EntityPicture(
            type=EntityPictureType.THUMB,
            url=picture_url,
            description="2082 Election Symbol. Source: Nepal Election Commission",
        )

        # Create party entity
        party_entity_data = {
            "slug": party_data["slug"],
            "names": names,
            "pictures": [picture],
            "attributions": [
                Attribution(
                    title=LangText(
                        en=LangTextValue(
                            value="Nepal Election Commission", provenance="human"
                        ),
                        ne=LangTextValue(value="नेपाल निर्वाचन आयोग", provenance="human"),
                    ),
                    details=LangText(
                        en=LangTextValue(
                            value=f"Registered Parties (2082) - imported {DATE}",
                            provenance="human",
                        ),
                        ne=LangTextValue(
                            value=f"दर्ता भएका दलहरू (२०८२) - आयात मिति {DATE} A.D.",
                            provenance="human",
                        ),
                    ),
                )
            ],
            "identifiers": identifiers,
            "address": address.model_dump(),
            "party_chief": party_chief.model_dump(),
            "registration_date": registration_date,
            "symbol": symbol.model_dump(),
        }

        # Create the entity
        party_entity = await context.publication.create_entity(
            entity_type=EntityType.ORGANIZATION,
            entity_subtype=EntitySubType.POLITICAL_PARTY,
            entity_data=party_entity_data,
            author_id=AUTHOR_ID,
            change_description=CHANGE_DESCRIPTION,
        )

        context.log(
            f"✓ Created party: {party_data['english_name']} ({party_data['slug']})"
        )
        created_count += 1

    context.log(f"Stage 1 complete: Created {created_count} new political parties")

    # STAGE 2: Fix existing party names
    context.log("Stage 2: Fixing existing party names...")
    existing_fixes = party_updates["existing_parties_fixes"]
    updated_count = 0

    for fix in existing_fixes:
        slug = fix["slug"]
        corrected_nepali_name = fix["corrected_nepali_name"]
        corrected_english_name = fix.get("corrected_english_name")
        fix_type = fix["type"]

        # Get the party by slug
        party_id = f"entity:organization/political_party/{slug}"
        party_entity = await context.db.get_entity(party_id)

        if not party_entity:
            context.log(f"⚠ Party not found: {slug}")
            continue

        # Get current primary name
        current_nepali_name = (
            party_entity.names[0].ne.full if party_entity.names[0].ne else None
        )

        if fix_type == "misspelled_name":
            # Update primary name with corrected version
            updated_names = [
                Name(
                    kind=NameKind.PRIMARY,
                    en=(
                        NameParts(full=corrected_english_name)
                        if corrected_english_name
                        else party_entity.names[0].en
                    ),
                    ne=NameParts(full=corrected_nepali_name),
                ).model_dump()
            ]

            # Preserve other existing names (skip the first one and any that match corrected name)
            if len(party_entity.names) > 1:
                for name in party_entity.names[1:]:
                    # Skip if this is the corrected name
                    if name.ne and name.ne.full == corrected_nepali_name:
                        continue
                    updated_names.append(name)

            # Add current name to misspelled_names
            if current_nepali_name and current_nepali_name != corrected_nepali_name:
                misspelled_name = Name(
                    kind=NameKind.ALTERNATE,
                    en=None,
                    ne=NameParts(full=current_nepali_name),
                )

                # Initialize or append to misspelled_names
                if party_entity.misspelled_names is None:
                    party_entity.misspelled_names = [misspelled_name]
                else:
                    party_entity.misspelled_names.append(misspelled_name)

            party_entity.names = updated_names

        else:  # alternative_name
            # Update primary name with corrected version
            updated_names = [
                Name(
                    kind=NameKind.PRIMARY,
                    en=(
                        NameParts(full=corrected_english_name)
                        if corrected_english_name
                        else party_entity.names[0].en
                    ),
                    ne=NameParts(full=corrected_nepali_name),
                ).model_dump()
            ]

            # Add current name as alternate if it's different from corrected
            if current_nepali_name and current_nepali_name != corrected_nepali_name:
                updated_names.append(
                    Name(
                        kind=NameKind.ALTERNATE,
                        en=None,
                        ne=NameParts(full=current_nepali_name),
                    ).model_dump()
                )

            # Preserve other existing names (skip the first one and any that match corrected or current name)
            if len(party_entity.names) > 1:
                for name in party_entity.names[1:]:
                    # Skip if this is the corrected name or current name
                    if name.ne and (
                        name.ne.full == corrected_nepali_name
                        or name.ne.full == current_nepali_name
                    ):
                        continue
                    updated_names.append(name)

            party_entity.names = updated_names

        # Update the entity
        await context.publication.update_entity(
            entity=party_entity,
            author_id=AUTHOR_ID,
            change_description=f"Fix party name: {current_nepali_name} → {corrected_nepali_name}",
        )

        context.log(
            f"✓ Fixed party name ({slug}): {current_nepali_name} → {corrected_nepali_name}"
        )
        updated_count += 1

    context.log(f"Stage 2 complete: Fixed {updated_count} existing party names")
    context.log("fix_political_parties completed successfully")


async def import_candidates(context: MigrationContext) -> None:
    """
    Import 2082 direct election candidates.

    This function:
    1. Loads all existing person entities into memory
    2. Loads candidate ID matches from 2079 to 2082
    3. For existing candidates: updates electoral history
    4. For new candidates: creates new person entities
    5. Ensures no slug collisions
    """
    context.log("Starting import_candidates...")

    # Load translations
    candidate_translations = context.read_json("data/translations.json")
    context.log(f"Loaded {len(candidate_translations)} candidate translations")

    # Load raw candidate data
    raw_candidates = context.read_json("data/DirectElectionResultCentral2082.json")
    candidate_lookup = {c["CandidateID"]: c for c in raw_candidates}
    context.log(f"Loaded {len(raw_candidates)} raw candidates")

    # Load candidate ID matches (2079 -> 2082)
    id_matches = {}
    with open(
        context.migration_dir / "data" / "candidate_id_matches_2079_2082.csv", "r"
    ) as f:
        reader = csv.DictReader(f)
        for row in reader:
            id_matches[int(row["y_2082"])] = int(row["y_2079"])
    context.log(f"Loaded {len(id_matches)} candidate ID matches")

    # Load district slug mapping
    district_slug_map = {}
    with open(
        context.migration_dir / "data" / "district-to-slug.csv", "r", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f)
        for row in reader:
            district_slug_map[row["district"]] = row["slug"]
    context.log(f"Loaded {len(district_slug_map)} district mappings")

    # Load all existing person entities into memory
    context.log("Loading all person entities into memory...")
    all_persons = await context.db.list_entities(
        entity_type="person", sub_type=None, limit=100_000
    )
    context.log(f"Loaded {len(all_persons)} person entities")

    # Build lookup by NEC candidate ID
    person_by_nec_id = {}
    for person in all_persons:
        if person.identifiers:
            for identifier in person.identifiers:
                if (
                    identifier.name
                    and identifier.name.en
                    and "nec_candidate_id" in identifier.name.en.value.lower()
                ):
                    person_by_nec_id[int(identifier.value)] = person
                    break
    context.log(f"Built lookup for {len(person_by_nec_id)} persons with NEC IDs")

    # Load party name to slug mapping
    context.log("Loading party-to-slug mapping...")
    party_to_slug = {}
    with open(
        context.migration_dir / "data/party-to-slug.csv", "r", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f)
        for row in reader:
            party_name = row["party"]
            slug = row["slug"]
            standardized = name_extractor.standardize_name(party_name)
            party_to_slug[standardized] = slug
    context.log(f"Loaded {len(party_to_slug)} party-to-slug mappings")

    # Load all political parties for linking (by slug)
    parties = await context.db.list_entities(
        entity_type="organization", sub_type="political_party", limit=1000
    )
    party_lookup = {}
    for party in parties:
        # Extract slug from party ID (format: entity:organization/political_party/{slug})
        if party.id.startswith("entity:organization/political_party/"):
            slug = party.id.replace("entity:organization/political_party/", "")
            party_lookup[slug] = party.id
    context.log(f"Loaded {len(party_lookup)} political parties for linking")

    # Process candidates
    new_candidates = []
    updated_candidates = []

    for candidate_id_str, translated in candidate_translations.items():
        candidate_id_2082 = int(candidate_id_str)
        raw = candidate_lookup.get(candidate_id_2082)

        if not raw:
            context.log(f"WARNING: No raw data for candidate ID {candidate_id_2082}")
            continue

        # Check if this candidate exists from 2079
        candidate_id_2079 = id_matches.get(candidate_id_2082)

        if candidate_id_2079 and candidate_id_2079 in person_by_nec_id:
            # Existing candidate - update electoral history
            person = person_by_nec_id[candidate_id_2079]
            updated_candidates.append((person, raw, translated, candidate_id_2082))
        else:
            # New candidate - create entity
            new_candidates.append((raw, translated, candidate_id_2082))

    context.log(f"Found {len(updated_candidates)} existing candidates to update")
    context.log(f"Found {len(new_candidates)} new candidates to create")

    # Update existing candidates
    context.log("Updating existing candidates with 2082 electoral history...")
    for person, raw, translated, candidate_id_2082 in updated_candidates:
        # Add new candidacy to electoral details
        party_id = _get_party_id(raw, party_to_slug, party_lookup, district_slug_map)
        constituency_id = _get_constituency_id(raw, district_slug_map)
        symbol = _build_symbol(raw, translated)

        new_candidacy = Candidacy(
            election_year=2082,
            election_type=ElectionType.FEDERAL,
            constituency_id=constituency_id,
            pa_subdivision=None,
            position=ElectionPosition.FEDERAL_PARLIAMENT,
            candidate_id=candidate_id_2082,
            party_id=party_id,
            votes_received=None,  # Election hasn't happened yet
            elected=False,
            symbol=symbol,
        )

        # Update electoral details
        if person.electoral_details:
            person.electoral_details.candidacies.append(new_candidacy)
        else:
            person.electoral_details = ElectoralDetails(candidacies=[new_candidacy])

        # Update tags
        if "federal-election-2082-candidate" not in person.tags:
            person.tags.append("federal-election-2082-candidate")

        # Update entity
        await context.publication.update_entity(
            entity=person,
            author_id=AUTHOR_ID,
            change_description=f"Added 2082 election candidacy",
        )

        context.log(
            f"✓ Updated: {person.names[0].ne.full if person.names[0].ne else person.names[0].en.full}"
        )

    context.log(f"Updated {len(updated_candidates)} existing candidates")

    # Create new candidates
    context.log("Creating new candidate entities...")

    # Build person data for all new candidates
    person_data_list = []
    for raw, translated, candidate_id_2082 in new_candidates:
        person_data = _build_person_data(
            candidate_id_2082,
            raw,
            translated,
            party_to_slug,
            party_lookup,
            district_slug_map,
        )
        person_data_list.append(person_data)

    # Check for slug collisions with existing entities
    existing_slugs = {p.slug for p in all_persons}
    for person_data in person_data_list:
        if person_data["slug"] in existing_slugs:
            person_data["slug"] = f"{person_data['slug']}-{person_data['candidate_id']}"

    # Check for duplicate slugs within new candidates
    slugs = [p["slug"] for p in person_data_list]
    duplicate_slugs = [s for s in set(slugs) if slugs.count(s) > 1]
    if duplicate_slugs:
        context.log(
            f"Found {len(duplicate_slugs)} duplicate slugs, adding candidate ID suffix"
        )
        context.log(f"Duplicate slugs: {', '.join(sorted(duplicate_slugs))}")
        for person_data in person_data_list:
            if person_data["slug"] in duplicate_slugs:
                old_slug = person_data["slug"]
                person_data["slug"] = (
                    f"{person_data['slug']}-{person_data['candidate_id']}"
                )
                context.log(f"  Renamed: {old_slug} → {person_data['slug']}")

    # Create entities
    for person_data in person_data_list:
        del person_data["candidate_id"]

        person = await context.publication.create_entity(
            entity_type=EntityType.PERSON,
            entity_subtype=None,
            entity_data=person_data,
            author_id=AUTHOR_ID,
            change_description=CHANGE_DESCRIPTION,
        )
        context.log(
            f"✓ Created: {person.names[0].ne.full if person.names[0].ne else person.names[0].en.full}"
        )

    context.log(f"Created {len(person_data_list)} new person entities")
    context.log("import_candidates completed successfully")


def _get_party_id(
    raw: dict, party_to_slug: dict, party_lookup: dict, district_slug_map: dict
) -> str | None:
    """Get party ID from party name using CSV mapping."""
    party_name = raw.get("PoliticalPartyName", "")
    if not party_name or party_name == "स्वतन्त्र":
        return None

    # Clean party name
    party_name = party_name.replace("(एकल चुनाव चिन्ह)", "").strip()
    standardized = name_extractor.standardize_name(party_name)

    # Look up slug from CSV mapping
    if standardized not in party_to_slug:
        raise Exception(
            f"No slug mapping found for party: {party_name}\n"
            f"Standardized to: {standardized}\n"
            f"Add this party to data/party-to-slug.csv"
        )

    slug = party_to_slug[standardized]

    # Look up party ID by slug
    if slug not in party_lookup:
        raise Exception(
            f"No party entity found with slug: {slug}\n"
            f"Party name: {party_name}\n"
            f"Expected entity ID: entity:organization/political_party/{slug}"
        )

    return party_lookup[slug]


def _get_constituency_id(raw: dict, district_slug_map: dict) -> str:
    """Build constituency ID from district and constituency number."""
    district_name = raw["DistrictName"]
    district_slug = district_slug_map.get(district_name)

    if not district_slug:
        raise Exception(f"No slug mapping for district: {district_name}")

    constituency_number = raw["SCConstID"]
    return f"entity:location/constituency/{district_slug}-{constituency_number}"


def _build_symbol(raw: dict, translated: dict) -> ElectionSymbol | None:
    """Build election symbol."""
    if not (raw.get("SYMBOLCODE") and raw.get("SymbolName")):
        return None

    symbol_en = (translated.get("symbol_name") or "").strip() or None

    return ElectionSymbol(
        symbol_name=LangText(
            en=(
                LangTextValue(value=symbol_en, provenance="translation_service")
                if symbol_en
                else None
            ),
            ne=LangTextValue(value=raw["SymbolName"], provenance="imported"),
        ),
        nec_id=int(raw["SYMBOLCODE"]),
    )


def _build_person_data(
    candidate_id: int,
    raw: dict,
    translated: dict,
    party_to_slug: dict,
    party_lookup: dict,
    district_slug_map: dict,
) -> dict:
    """Build person entity data for new candidate."""

    # Personal details (NO family information per migration 007)
    age = raw.get("AGE_YR")

    gender_map = {"पुरुष": Gender.MALE, "महिला": Gender.FEMALE}
    gender = gender_map.get(raw.get("Gender", ""), Gender.OTHER)

    # Address
    addr_en = (translated.get("address") or "").strip() or None
    addr_ne = (raw.get("ADDRESS") or "").strip() or None

    # Education
    education = None
    inst_en = (translated.get("education_institution") or "").strip() or None
    inst_ne = (raw.get("NAMEOFINST") or "").strip() or None
    degree_en = (translated.get("education_level") or "").strip() or None
    field_en = (translated.get("education_field") or "").strip() or None

    if inst_en or inst_ne or degree_en or field_en:
        education = [
            Education(
                institution=(
                    LangText(
                        en=(
                            LangTextValue(
                                value=inst_en, provenance="translation_service"
                            )
                            if inst_en
                            else None
                        ),
                        ne=(
                            LangTextValue(value=inst_ne, provenance="imported")
                            if inst_ne
                            else None
                        ),
                    )
                    if inst_en or inst_ne
                    else LangText()
                ),
                degree=(
                    LangText(en=LangTextValue(value=degree_en, provenance="llm"))
                    if degree_en
                    else None
                ),
                field=(
                    LangText(en=LangTextValue(value=field_en, provenance="llm"))
                    if field_en
                    else None
                ),
            )
        ]

    # Positions
    positions = None
    title_en = (translated.get("position_title") or "").strip() or None
    org_en = (translated.get("organization") or "").strip() or None
    desc_en = (translated.get("description") or "").strip() or None

    if title_en or org_en:
        positions = [
            Position(
                title=(
                    LangText(en=LangTextValue(value=title_en, provenance="llm"))
                    if title_en
                    else LangText()
                ),
                organization=(
                    LangText(en=LangTextValue(value=org_en, provenance="llm"))
                    if org_en
                    else None
                ),
                description=desc_en[:200] if desc_en else None,
            )
        ]

    personal_details = PersonDetails(
        birth_date=None,
        gender=gender,
        address=(
            Address(
                description2=LangText(
                    en=(
                        LangTextValue(value=addr_en, provenance="translation_service")
                        if addr_en
                        else None
                    ),
                    ne=(
                        LangTextValue(value=addr_ne, provenance="imported")
                        if addr_ne
                        else None
                    ),
                )
            )
            if addr_en or addr_ne
            else None
        ),
        education=education,
        positions=positions,
    )

    # Electoral details
    party_id = _get_party_id(raw, party_to_slug, party_lookup, district_slug_map)
    constituency_id = _get_constituency_id(raw, district_slug_map)
    symbol = _build_symbol(raw, translated)

    candidacy = Candidacy(
        election_year=2082,
        election_type=ElectionType.FEDERAL,
        constituency_id=constituency_id,
        pa_subdivision=None,
        position=ElectionPosition.FEDERAL_PARLIAMENT,
        candidate_id=candidate_id,
        party_id=party_id,
        votes_received=None,  # Election hasn't happened yet
        elected=False,
        symbol=symbol,
    )

    electoral_details = ElectoralDetails(candidacies=[candidacy])

    # Attributes
    qual_en = (translated.get("qualification") or "").strip() or None
    qual_ne = (raw.get("QUALIFICATION") or "").strip() or None
    other_en = (translated.get("other_details") or "").strip() or None
    other_ne = (raw.get("OTHERDETAILS") or "").strip() or None

    # Age attribute
    age_text = None
    if age and isinstance(age, int):
        age_text = LangText(
            en=LangTextValue(
                value=f"Aged {age} as of January 2026", provenance="imported"
            ),
            ne=LangTextValue(value=f"२०८२ माघमा {age} वर्ष", provenance="imported"),
        ).model_dump()

    attributes = {
        "election_council_misc": {
            "age": age_text,
            "qualification": (
                LangText(
                    en=(
                        LangTextValue(value=qual_en, provenance="translation_service")
                        if qual_en
                        else None
                    ),
                    ne=(
                        LangTextValue(value=qual_ne, provenance="imported")
                        if qual_ne
                        else None
                    ),
                ).model_dump()
                if qual_en or qual_ne
                else None
            ),
            "other_details": (
                LangText(
                    en=(
                        LangTextValue(value=other_en, provenance="translation_service")
                        if other_en
                        else None
                    ),
                    ne=(
                        LangTextValue(value=other_ne, provenance="imported")
                        if other_ne
                        else None
                    ),
                ).model_dump()
                if other_en or other_ne
                else None
            ),
        }
    }

    # Build slug
    slug = text_to_slug(translated["name"])

    return {
        "slug": slug,
        "candidate_id": candidate_id,
        "tags": ["federal-election-2082-candidate"],
        "names": [
            Name(
                kind=NameKind.PRIMARY,
                en=NameParts(full=name_extractor.standardize_name(translated["name"])),
                ne=NameParts(
                    full=name_extractor.standardize_name(raw["CandidateName"])
                ),
            ).model_dump()
        ],
        "attributes": attributes,
        "attributions": [
            Attribution(
                title=LangText(
                    en=LangTextValue(
                        value="Nepal Election Commission - 2082 candidates",
                        provenance="human",
                    ),
                    ne=LangTextValue(
                        value="नेपाल निर्वाचन आयोग - २०८२ को उम्मेदवार",
                        provenance="human",
                    ),
                ),
                details=LangText(
                    en=LangTextValue(
                        value=f"2082 Election Candidates - imported {DATE}",
                        provenance="human",
                    ),
                    ne=LangTextValue(
                        value=f"२०८२ निर्वाचन उम्मेदवार - आयात मिति {DATE} A.D.",
                        provenance="human",
                    ),
                ),
            )
        ],
        "personal_details": personal_details.model_dump(),
        "identifiers": [
            ExternalIdentifier(
                scheme="other",
                name=LangText(
                    en=LangTextValue(value="nec_candidate_id", provenance="human"),
                    ne=LangTextValue(value="निर्वाचन आयोग दर्ता नं०", provenance="human"),
                ),
                value=str(candidate_id),
            )
        ],
        "electoral_details": electoral_details.model_dump(),
        "pictures": [
            EntityPicture(
                type=EntityPictureType.THUMB,
                url=f"https://assets.nes.newnepal.org/assets/images/election-commission-2082-pictures/{candidate_id}.jpg",
                description="Source: Nepal Election Commission",
            )
        ],
    }


async def migrate(context: MigrationContext) -> None:
    """
    Main migration function for 2082 direct candidates.

    Step 1: Fix political parties (create new, update existing names)
    Step 2: Import 2082 direct election candidates
    """
    context.log("Migration 010-source-2082-direct-candidates started")

    # Execute step 1: Fix political parties
    await fix_political_parties(context)

    # Execute step 2: Import candidates
    await import_candidates(context)

    context.log("Migration completed successfully")
