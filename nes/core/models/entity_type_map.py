"""Entity type/subtype mapping for nes with Nepali-specific classifications.

This module defines the valid combinations of entity types and subtypes,
reflecting Nepal's political and administrative structure.

ALLOWED_ENTITY_PREFIXES is the canonical registry of valid entity_prefix values.
It is a flat set of slash-joined strings (e.g. "organization/political_party").
New prefixes — including 3-level ones like "organization/nepal_govt/moha" — are
added here to make them available for use in entity IDs.

ENTITY_TYPE_MAP is retained for backward compatibility.
"""

from nes.core.models.entity import EntitySubType, EntityType

# ---------------------------------------------------------------------------
# Canonical prefix registry (replaces ENTITY_TYPE_MAP for validation)
# ---------------------------------------------------------------------------

# All valid entity_prefix values. Seeded from existing type/subtype combos.
# To add a new classification, append its slash-joined prefix string here.
ALLOWED_ENTITY_PREFIXES: set[str] = {
    # Person — no subtypes
    "person",
    # Organization
    "organization",
    "organization/political_party",
    "organization/government_body",
    "organization/ngo",
    "organization/international_org",
    "organization/hospital",
    # Location — Nepal's administrative hierarchy
    "location",
    "location/province",
    "location/district",
    "location/metropolitan_city",
    "location/sub_metropolitan_city",
    "location/municipality",
    "location/rural_municipality",
    "location/ward",
    "location/constituency",
    # Project
    "project",
    "project/development_project",
}

# ---------------------------------------------------------------------------
# Legacy type map (deprecated — use ALLOWED_ENTITY_PREFIXES for new code)
# ---------------------------------------------------------------------------

# Entity type map for v2 with Nepali context
# This maps entity types to their allowed subtypes
ENTITY_TYPE_MAP = {
    EntityType.PERSON: {
        None,  # Person entities do not have subtypes
        # All persons (politicians, civil servants, activists, etc.) use the same type
        # Roles and positions are captured in attributes
    },
    EntityType.ORGANIZATION: {
        None,  # Organization without specific subtype
        EntitySubType.POLITICAL_PARTY,  # Nepali political parties
        EntitySubType.GOVERNMENT_BODY,  # Government ministries, departments, constitutional bodies
        EntitySubType.HOSPITAL,  # Hospitals and health facilities
        EntitySubType.NGO,  # Non-governmental organizations
        EntitySubType.INTERNATIONAL_ORG,  # International organizations in Nepal
    },
    EntityType.LOCATION: {
        None,  # Location without specific subtype
        # Nepal's administrative hierarchy (federal structure since 2015)
        EntitySubType.PROVINCE,  # 7 provinces (प्रदेश)
        EntitySubType.DISTRICT,  # 77 districts (जिल्ला)
        EntitySubType.METROPOLITAN_CITY,  # 6 metropolitan cities (महानगरपालिका)
        EntitySubType.SUB_METROPOLITAN_CITY,  # 11 sub-metropolitan cities (उपमहानगरपालिका)
        EntitySubType.MUNICIPALITY,  # 276 municipalities (नगरपालिका)
        EntitySubType.RURAL_MUNICIPALITY,  # 460 rural municipalities (गाउँपालिका)
        EntitySubType.WARD,  # Wards within municipalities (वडा)
        EntitySubType.CONSTITUENCY,  # Electoral constituencies (निर्वाचन क्षेत्र)
    },
    EntityType.PROJECT: {
        None,  # Project without specific subtype
        EntitySubType.DEVELOPMENT_PROJECT,  # Development projects (विकास परियोजना)
    },
}


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
