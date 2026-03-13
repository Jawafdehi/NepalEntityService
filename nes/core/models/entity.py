"""Entity model using Pydantic for nes."""

from abc import ABC
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from nes.core.identifiers import build_entity_id, build_entity_id_from_prefix

from ..constraints import (
    MAX_PREFIX_DEPTH,
    MAX_SLUG_LENGTH,
    MIN_SLUG_LENGTH,
    SLUG_PATTERN,
)
from .base import Attribution, Contact, EntityPicture, LangText, Name, NameKind
from .version import VersionSummary


class IdentifierScheme(str, Enum):
    """External identifier schemes."""

    WIKIPEDIA = "wikipedia"
    WIKIDATA = "wikidata"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    WEBSITE = "website"
    OTHER = "other"


class ExternalIdentifier(BaseModel):
    """A normalized external identifier reference."""

    scheme: IdentifierScheme = Field(..., description="Type of external identifier")
    name: Optional[LangText] = Field(
        None, description="Name of the external identifier"
    )
    value: str = Field(..., min_length=1, description="Identifier value")
    url: Optional[AnyUrl] = Field(None, description="URL to the external resource")


class EntityType(str, Enum):
    """Types of entities."""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    PROJECT = "project"


class EntitySubType(str, Enum):
    """Subtypes for entities with Nepali-specific classifications.

    Note: Person entities do not have subtypes in this system.

    Organization Subtypes:
    - POLITICAL_PARTY: Registered political parties in Nepal (e.g., Nepali Congress, CPN-UML)
    - GOVERNMENT_BODY: Government ministries, departments, and constitutional bodies
    - NGO: Non-governmental organizations operating in Nepal
    - INTERNATIONAL_ORG: International organizations with presence in Nepal

    Location Subtypes (Nepal's Administrative Hierarchy):
    - PROVINCE: Nepal's 7 provinces (प्रदेश) - highest administrative division
    - DISTRICT: Nepal's 77 districts (जिल्ला) - second-level administrative division
    - METROPOLITAN_CITY: Mahanagarpalika (महानगरपालिका) - 6 cities with >300k population
    - SUB_METROPOLITAN_CITY: Upamahanagarpalika (उपमहानगरपालिका) - cities with 100k-300k population
    - MUNICIPALITY: Nagarpalika (नगरपालिका) - urban local bodies
    - RURAL_MUNICIPALITY: Gaunpalika (गाउँपालिका) - rural local bodies
    - WARD: Smallest administrative unit within municipalities
    - CONSTITUENCY: Electoral constituencies for parliamentary elections
    """

    # Organization subtypes
    POLITICAL_PARTY = "political_party"  # राजनीतिक दल
    GOVERNMENT_BODY = "government_body"  # सरकारी निकाय
    NGO = "ngo"  # गैर सरकारी संस्था
    INTERNATIONAL_ORG = "international_org"  # अन्तर्राष्ट्रिय संस्था
    HOSPITAL = "hospital"  # अस्पताल

    # Location subtypes - Nepal's administrative hierarchy
    PROVINCE = "province"  # प्रदेश (7 provinces)
    DISTRICT = "district"  # जिल्ला (77 districts)
    METROPOLITAN_CITY = "metropolitan_city"  # महानगरपालिका (6 metropolitan cities)
    SUB_METROPOLITAN_CITY = (
        "sub_metropolitan_city"  # उपमहानगरपालिका (11 sub-metropolitan cities)
    )
    MUNICIPALITY = "municipality"  # नगरपालिका (276 municipalities)
    RURAL_MUNICIPALITY = "rural_municipality"  # गाउँपालिका (460 rural municipalities)
    WARD = "ward"  # वडा (smallest unit)
    CONSTITUENCY = "constituency"  # निर्वाचन क्षेत्र (electoral constituency)

    # Project subtypes
    DEVELOPMENT_PROJECT = "development_project"  # विकास परियोजना


Attributes = Dict[str, Any]


class Entity(BaseModel, ABC):
    """Base entity model. Cannot be instantiated directly - use Person, Organization, or Location.

    At least one name with kind='PRIMARY' should be provided for all entities.
    """

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(
        ...,
        min_length=MIN_SLUG_LENGTH,
        max_length=MAX_SLUG_LENGTH,
        pattern=SLUG_PATTERN,
        description="URL-friendly identifier for the entity",
    )
    entity_prefix: Optional[str] = Field(
        None,
        description=(
            "N-level classification prefix (e.g. 'organization/nepal_govt/moha'). "
            "When set, takes precedence over type/sub_type for ID generation. "
            "Must be 1-MAX_PREFIX_DEPTH slash-separated segments."
        ),
    )
    type: EntityType = Field(
        ...,
        description="Type of entity",
    )
    sub_type: Optional[EntitySubType] = Field(
        None,
        description="Subtype classification for the entity (deprecated: use entity_prefix)",
    )
    names: List[Name] = Field(
        ..., description="List of names associated with the entity"
    )
    misspelled_names: Optional[List[Name]] = Field(
        None, description="List of misspelled or alternative name variations"
    )
    version_summary: VersionSummary = Field(
        ..., description="Summary of the latest version information"
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the entity was created"
    )
    identifiers: Optional[List[ExternalIdentifier]] = Field(
        None, description="External identifiers for the entity"
    )
    tags: Optional[List[str]] = Field(
        None, description="Tags for categorizing the entity"
    )
    attributes: Optional[Attributes] = Field(
        None,
        description="Additional attributes for the entity.",
    )
    contacts: Optional[List[Contact]] = Field(
        None, description="Contact information for the entity"
    )
    short_description: Optional[LangText] = Field(
        None,
        description="Brief description of the entity",
    )
    description: Optional[LangText] = Field(
        None,
        description="Detailed description of the entity",
    )
    attributions: Optional[List[Attribution]] = Field(
        None, description="Sources and attributions for the entity data"
    )
    pictures: Optional[List[EntityPicture]] = Field(
        None, description="Pictures associated with the entity"
    )

    @field_validator("entity_prefix")
    @classmethod
    def validate_entity_prefix_depth(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v:
            raise ValueError("entity_prefix must not be empty")
        segments = v.split("/")
        if any(s == "" for s in segments):
            raise ValueError(f"entity_prefix '{v}' contains empty segments")
        depth = len(segments)
        if depth > MAX_PREFIX_DEPTH:
            raise ValueError(
                f"entity_prefix '{v}' has depth {depth} which exceeds "
                f"MAX_PREFIX_DEPTH={MAX_PREFIX_DEPTH}"
            )
        return v

    @computed_field
    @property
    def id(self) -> str:
        # entity_prefix takes precedence over type/sub_type when set
        if self.entity_prefix is not None:
            return build_entity_id_from_prefix(self.entity_prefix, self.slug)
        # Fallback: backward-compat path using type + sub_type
        type_val = self.type.value if hasattr(self.type, "value") else self.type
        subtype_val = (
            self.sub_type.value
            if (self.sub_type and hasattr(self.sub_type, "value"))
            else self.sub_type
        )
        return build_entity_id(type_val, subtype_val, self.slug)

    @model_validator(mode="after")
    def validate_not_base_entity(self) -> "Entity":
        """Prevent direct instantiation of Entity class."""
        if self.__class__.__name__ == "Entity":
            raise ValueError(
                "Cannot instantiate Entity directly. Use Person, Organization, or Location instead."
            )
        return self

    @model_validator(mode="after")
    def validate_entity_prefix_matches_type(self) -> "Entity":
        """Ensure the first segment of entity_prefix matches the declared type."""
        if self.entity_prefix is not None:
            prefix_root = self.entity_prefix.split("/")[0]
            type_val = self.type.value if hasattr(self.type, "value") else self.type
            if prefix_root != type_val:
                raise ValueError(
                    f"entity_prefix '{self.entity_prefix}' root '{prefix_root}' "
                    f"does not match entity type '{type_val}'"
                )
        return self

    @field_validator("names")
    @classmethod
    def validate_names(cls, v: List[Name]):
        if not any(name.kind == NameKind.PRIMARY for name in v):
            raise ValueError(
                f'At least one name with kind="{NameKind.PRIMARY}" is required'
            )

        return v
