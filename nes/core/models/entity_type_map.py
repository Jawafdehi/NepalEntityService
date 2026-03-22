"""Entity type/subtype mapping for nes with Nepali-specific classifications.

This module defines the valid combinations of entity types and subtypes,
reflecting Nepal's political and administrative structure.

ENTITY_PREFIX_MAP is the canonical registry mapping entity_prefix values to their
corresponding model classes. It is a flat dict of slash-joined strings
(e.g. "organization/political_party") to Entity subclasses.

ALLOWED_ENTITY_PREFIXES is derived from ENTITY_PREFIX_MAP keys.
"""

# Import Entity subclasses (avoiding circular imports by importing here)
from typing import TYPE_CHECKING, Dict, Type

# ---------------------------------------------------------------------------
# Canonical prefix-to-class map
# ---------------------------------------------------------------------------


if TYPE_CHECKING:
    from nes.core.models.entity import Entity


# Lazy imports to avoid circular dependencies
def _get_entity_prefix_map() -> Dict[str, Type["Entity"]]:
    """Get the entity prefix map with lazy imports."""
    from nes.core.models.location import Location
    from nes.core.models.organization import (
        GovernmentBody,
        Hospital,
        Organization,
        PoliticalParty,
    )
    from nes.core.models.person import Person
    from nes.core.models.project import Project

    return {
        # Person entities (no subtypes)
        "person": Person,
        # Organization entities
        "organization": Organization,
        "organization/political_party": PoliticalParty,
        "organization/government_body": GovernmentBody,  # TODO: Deprecate this.
        "organization/government": GovernmentBody,
        "organization/government/federal": GovernmentBody,
        # Commission entities (constitutional bodies and their branches)
        "organization/government/commission/federal": GovernmentBody,
        "organization/government/commission/province": GovernmentBody,
        "organization/government/commission/regional": GovernmentBody,
        "organization/government/commission/district": GovernmentBody,
        "organization/hospital": Hospital,
        "organization/ngo": Organization,
        "organization/international_org": Organization,
        # Location entities
        "location": Location,
        "location/province": Location,
        "location/district": Location,
        "location/metropolitan_city": Location,
        "location/sub_metropolitan_city": Location,
        "location/municipality": Location,
        "location/rural_municipality": Location,
        "location/ward": Location,
        "location/constituency": Location,
        # Project entities
        "project": Project,
        "project/development_project": Project,
    }


# Flat map from entity_prefix to entity class
# This provides a direct lookup for entity class based on the full prefix path
ENTITY_PREFIX_MAP: Dict[str, Type["Entity"]] = _get_entity_prefix_map()

# Canonical set of allowed entity prefixes (derived from ENTITY_PREFIX_MAP keys)
ALLOWED_ENTITY_PREFIXES: set[str] = set(ENTITY_PREFIX_MAP.keys())

# Nepali administrative hierarchy documentation
NEPALI_ADMINISTRATIVE_HIERARCHY = """
Nepal's Federal Administrative Structure (since 2015 Constitution):

Level 1: Federal Government (संघीय सरकार)
  - National government based in Kathmandu

Level 2: Provincial Government (प्रादेशिक सरकार)
  - 7 Provinces (प्रदेश):
    1. Koshi Province (कोशी प्रदेश)
    2. Madhesh Province (मधेश प्रदेश)
    3. Bagmati Province (बागमती प्रदेश)
    4. Gandaki Province (गण्डकी प्रदेश)
    5. Lumbini Province (लुम्बिनी प्रदेश)
    6. Karnali Province (कर्णाली प्रदेश)
    7. Sudurpashchim Province (सुदूरपश्चिम प्रदेश)

Level 3: District (जिल्ला)
  - 77 Districts across all provinces
  - Historical administrative units maintained in federal structure

Level 4: Local Government (स्थानीय तह)
  - 753 Local Bodies total:
    * 6 Metropolitan Cities (महानगरपालिका) - population > 300,000
    * 11 Sub-Metropolitan Cities (उपमहानगरपालिका) - population 100,000-300,000
    * 276 Municipalities (नगरपालिका) - urban areas
    * 460 Rural Municipalities (गाउँपालिका) - rural areas

Level 5: Ward (वडा)
  - Smallest administrative unit
  - Each local body divided into multiple wards
  - Total: 6,743 wards across Nepal

Electoral System:
  - Parliamentary constituencies (निर्वाचन क्षेत्र) for House of Representatives
  - 165 constituencies for First-Past-The-Post (FPTP) elections
  - Provincial constituencies for Provincial Assembly elections
"""


# Political party classifications
NEPALI_POLITICAL_SPECTRUM = """
Nepal's Political Landscape:

Major Political Ideologies:
  - Communist/Socialist: CPN-UML, CPN (Maoist Centre), Nepal Communist Party
  - Social Democratic: Nepali Congress, Nepal Samajbadi Party
  - Monarchist/Hindu Nationalist: Rastriya Prajatantra Party
  - New/Reform: Rastriya Swatantra Party, Bibeksheel Sajha Party

Party Registration:
  - Parties must be registered with Election Commission of Nepal
  - Must meet minimum membership and organizational requirements
  - Subject to periodic renewal and compliance checks

Coalition Politics:
  - Nepal typically has coalition governments
  - Parties form pre-election or post-election alliances
  - Frequent government changes due to coalition dynamics
"""
