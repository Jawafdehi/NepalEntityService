"""
Migration: 005-seed-2079-election-candidates
Description: Import 2079 election candidates as Person entities
Author: Damodar Dahal
Date: 2025-11-09
"""

from datetime import date

from nepali_date_utils import converter

from nes.core.identifiers.builders import break_entity_id, build_entity_id
from nes.core.models import (
    Address,
    Attribution,
    EntityPicture,
    EntityPictureType,
    LangText,
    LangTextValue,
    Name,
    NameParts,
)
from nes.core.models.entity import EntitySubType, EntityType, ExternalIdentifier
from nes.core.models.location import LocationType
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
from nes.core.models.version import Author
from nes.core.utils.slug_helper import text_to_slug
from nes.services.migration.context import MigrationContext
from nes.services.scraping.normalization import NameExtractor

AUTHOR = "Damodar Dahal"
DATE = "2025-11-12"
DESCRIPTION = "Import 2079 election candidates as Person entities"
CHANGE_DESCRIPTION = "Initial sourcing from 2079 election results"

# CSV to database district name mapping
DISTRICT_NAME_MAP = {
    "अर्घाखांची": "arghakhanchi",
    "कन्चनपुर": "kanchanpur",
    "काठमाडौं": "kathmandu",
    "काभ्रेपलाञ्चोक": "kavrepalanchok",
    "खोटाङ्ग": "khotang",
    "तेर्हथुम": "terhathum",
    "धादिङ्ग": "dhading",
    "नवलपरासी (बर्दघाट सुस्ता पश्चिम)": "parasi",
    "नवलपरासी (बर्दघाट सुस्ता पूर्व)": "nawalpur",
    "पाँचथर": "pachthar",
    "प्यूठान": "pyuthan",
    "बझाङ्ग": "bajhang",
    "मनाङ्ग": "manang",
    "मुस्तांग": "mustang",
    "मोरङ्ग": "morang",
    "रुकुम पूर्व": "eastern-rukum",
    "लमजुंग": "lamjung",
    "सोलुखुम्बु": "solukhumbu",
    "स्याङ्जा": "syangja",
}

PARTY_ADDITIONAL_NAME_MAP = {
    "जनता समाजवादी पार्टी, नेपाल": "जनता समाजवादी पार्टी, नेपाल",
    "खम्बुवान राष्ट्रिय मोर्चा नेपाल": "खम्बुवान राष्ट्रिय मोर्चा, नेपाल",
    "सचेत नेपाली पार्टी": "सचेत नेपाली पार्टी",
    "पुनर्जागरण पार्टी नेपाल": "पुनर्जागरण पार्टी, नेपाल",
    "मंगोल नेशनल अर्गनाइजेसन": "मंगोल नेशनल अर्गनाइजेशन",
    "नेपाल सद्भावना पार्टी": "राष्ट्रिय सदभावना पार्टी",
    "नेपाल कम्युनिष्ट पार्टी (एकिकृत समाजबादी)": "नेपाल कम्युनिष्ट पार्टी (एकीकृत समाजवादी)",
    "तराइ-मधेश लोकतान्त्रिक पार्टी": "तराई-मधेश लोकतान्त्रिक पार्टी",
    "लोकतान्त्रिक समाजवादी पार्टी, नेपाल": "लोकतान्त्रिक समाजवादी पार्टी नेपाल",
    "जनता प्रगतिशिल पार्टी, नेपाल": "जनता प्रगतिशील पार्टी, नेपाल",
    "नेपाल कम्युनिष्ट पार्टी (एमाले)": "नेपाल कम्युनिष्ट पार्टी (एकीकृत मार्क्सवादी लेनिनवादी)",
    "राष्ट्रिय मुक्ति आन्दोलन नेपाल": "राष्ट्रिय मुक्ति आन्दोलन, नेपाल",
    "नेपाल कम्युनिष्ट पार्टी (मार्क्सवादी लेनिनवादी)": "नेपाल कम्युनिष्ट पार्टी (मार्क्सवादी-लेनिनवादी)",
    "साझा पार्टी नेपाल": "साझा पार्टी, नेपाल",
    "संघीय लोकतान्त्रिक राष्ट्रिय मञ्च": "संघीय लोकतान्त्रिक राष्ट्रिय मत",
    "जनसमाजवादी पार्टी नेपाल": "जनसमाजवादी पार्टी, नेपाल",
    "किरात खम्बुवान साझा पार्टी": "राष्ट्रिय साझा पार्टी",
    "आमूल परिवर्तन मसिहा पार्टी नेपाल": "आमूल परिवर्तन रिपब्लिकन पार्टी नेपाल",
    "तामाङसालिङ लोकतान्त्रिक पार्टी": "जनप्रिय लोकतान्त्रिक पार्टी",
    "पिछडावर्ग निषाद दलित जनजाती पार्टी": "विकासशील जनता पार्टी",
    "एकीकृत शक्ति नेपाल": "नागरिक शक्ति, नेपाल",
    "नेपाल सुशासन पार्टी": "राष्ट्रिय मातृभूमि पार्टी",
    "नेपाल आमा पार्टी": "राष्ट्रिय मातृभूमि पार्टी",
    "नेपाल दलित पार्टी": "नेपाल मानवतावादी पार्टी",
    "नेपाल समाजवादी पार्टी": "नेपाल कम्युनिष्ट पार्टी (माओवादी केन्द्र)",
    "संघीय लोकतान्त्रिक राष्ट्रिय मञ्च(थरुहट)": "संघीय नेपाल पार्टी",
    "सामाजिक एकता पार्टी": "संयुक्त नागरिक पार्टी",
    "इतिहासिक प्रजातान्त्रिक जनता पार्टी नेपाल": "इतिहासिक जनता पार्टी",
    "नेपाली काँग्रेस": "नेपाली कांग्रेस",
}


class CandidateMigration:
    def __init__(self, context: MigrationContext):
        self.context = context
        self.name_extractor = NameExtractor()
        self.author_id = None
        self.candidate_lookup = {}  # CandidateID -> raw candidate data
        self.party_lookup = {}  # Standardized party name -> entity ID
        self.district_id_map = {}  # District name (Nepali) -> entity ID
        self.constituency_map = {}  # constituency entity ID -> Location entity

    async def run(self):
        self.context.log("Migration started: Importing 2079 election candidates")
        await self._setup_author()
        candidate_translations = self._load_data()
        await self._build_lookups()
        await self._identify_missing_parties()
        await self._process_candidates(candidate_translations)
        await self._verify()
        self.context.log("Migration completed successfully")

    async def _identify_missing_parties(self):
        """Identify all party names that cannot be resolved."""
        missing_parties = set()
        for candidate_id, raw in self.candidate_lookup.items():
            party_name = raw.get("PoliticalPartyName", "")
            if party_name and party_name != "स्वतन्त्र":
                if self._get_party_id(party_name, collect_missing=True) is None:
                    missing_parties.add(party_name)

        if missing_parties:
            self.context.log("\n=== MISSING PARTIES ===")
            for party in sorted(missing_parties):
                self.context.log(
                    f'    "{party}": "",  # TODO: Map to correct party name'
                )
            self.context.log("======================\n")
            raise Exception(
                f"Found {len(missing_parties)} unresolved party names. See log above."
            )

    async def _setup_author(self):
        author = Author(slug=text_to_slug(AUTHOR), name=AUTHOR)
        await self.context.db.put_author(author)
        self.author_id = author.id
        self.context.log(f"Created author: {author.name} ({author.id})")

    def _load_data(self):
        candidate_translations = self.context.read_json("source/translations.json")
        self.context.log(f"Loaded {len(candidate_translations)} candidate translations")

        central_data = self.context.read_json("source/ElectionResultCentral2079.json")
        state_data = self.context.read_json("source/ElectionResultState2079.json")
        for row in central_data:
            row["central"] = True

        all_candidates = central_data + state_data
        self.candidate_lookup = {c["CandidateID"]: c for c in all_candidates}
        self.context.log(
            f"Loaded {len(all_candidates)} candidates from election results"
        )

        return candidate_translations

    async def _build_lookups(self):
        parties = await self.context.db.list_entities(
            entity_type="organization", sub_type="political_party", limit=1000
        )
        for party in parties:
            for name in party.names:
                if name.ne and name.ne.full:
                    self.party_lookup[
                        self.name_extractor.standardize_name(name.ne.full)
                    ] = party.id
        self.context.log(
            f"Loaded {len(self.party_lookup)} political parties for linking"
        )

        districts = await self.context.search.search_entities(
            entity_type=EntityType.LOCATION, sub_type=EntitySubType.DISTRICT, limit=77
        )
        self.district_id_map = {d.names[0].ne.full: d.id for d in districts}

        constituencies = await self.context.search.search_entities(
            entity_type=EntityType.LOCATION,
            sub_type=EntitySubType.CONSTITUENCY,
            limit=500,
        )
        for c in constituencies:
            self.constituency_map[c.id] = c
        self.context.log(
            f"Loaded {len(self.constituency_map)} constituencies for linking"
        )

    def _get_party_id(
        self, party_name: str, collect_missing: bool = False
    ) -> str | None:
        if party_name == "स्वतन्त्र":
            return None
        original_name = party_name
        party_name = party_name.replace("(एकल चुनाव चिन्ह)", "")

        # Try mapping first
        if party_name in PARTY_ADDITIONAL_NAME_MAP:
            party_name = PARTY_ADDITIONAL_NAME_MAP[party_name]

        party_name = self.name_extractor.standardize_name(party_name)
        if party_name not in self.party_lookup:
            if collect_missing:
                return None
            raise Exception(
                f"No political party found for {party_name} (original: {original_name})"
            )
        return self.party_lookup[party_name]

    def _get_district_id(self, district_name_ne: str) -> str:
        if district_name_ne in self.district_id_map:
            return self.district_id_map[district_name_ne]

        # Try using the mapping
        if district_name_ne in DISTRICT_NAME_MAP:
            district_slug = DISTRICT_NAME_MAP[district_name_ne]
            district_id = build_entity_id(
                type="location", subtype=LocationType.DISTRICT.value, slug=district_slug
            )
            if district_id in [d_id for d_id in self.district_id_map.values()]:
                return district_id

        raise Exception(f"District {district_name_ne} not found")

    def _get_constituency_id(self, raw: dict) -> str:
        district_id = self._get_district_id(raw["DistrictName"])
        district_slug = break_entity_id(district_id).slug

        constituency_number = (
            raw["SCConstID"] if raw.get("central") else raw["CenterConstID"]
        )

        entity_id = build_entity_id(
            type="location",
            subtype=LocationType.CONSTITUENCY.value,
            slug=f"{district_slug}-{constituency_number}",
        )

        assert entity_id in self.constituency_map

        return entity_id

    async def _process_candidates(self, candidate_translations: dict):
        # Build list of all person data
        person_data_list = []
        for candidate_id, translated in candidate_translations.items():
            candidate_id = int(candidate_id)
            raw = self.candidate_lookup.get(candidate_id)
            if not raw:
                self.context.log(
                    f"WARNING: No raw data for candidate ID {candidate_id}"
                )
                continue

            person_data = await self._build_person_data(candidate_id, raw, translated)
            person_data_list.append(person_data)

        self.context.log(f"Built {len(person_data_list)} person entities")

        # Fix duplicate slugs by adding candidate ID suffix
        slugs = [p["slug"] for p in person_data_list]
        duplicate_slugs = [s for s in set(slugs) if slugs.count(s) > 1]
        if duplicate_slugs:
            self.context.log(
                f"Found {len(duplicate_slugs)} duplicate slugs, adding candidate ID suffix"
            )
            for person_data in person_data_list:
                if person_data["slug"] in duplicate_slugs:
                    person_data["slug"] = (
                        f"{person_data['slug']}-{person_data['candidate_id']}"
                    )

        # Create entities in DB one by one
        for person_data in person_data_list:
            del person_data["candidate_id"]

            person = await self.context.publication.create_entity(
                entity_type=EntityType.PERSON,
                entity_subtype=None,
                entity_data=person_data,
                author_id=self.author_id,
                change_description=CHANGE_DESCRIPTION,
            )
            self.context.log(f"Created person {person.id}")

        self.context.log(f"Created {len(person_data_list)} person entities")

    async def _build_person_data(
        self, candidate_id: int, raw: dict, translated: dict
    ) -> dict:
        personal_details = self._build_personal_details(raw, translated)
        electoral_details = self._build_electoral_details(candidate_id, raw, translated)
        attributes = self._build_attributes(raw, translated)
        tags = self._build_tags(raw, electoral_details.candidacies[0])

        slug = text_to_slug(translated["name"])
        # Special case: For candidate ID 333804, named BP koirala, include candidate ID in slug
        # This is needed because it collides with the BP from 000-example-migration.
        if candidate_id == 333804:
            slug = f"{slug}-{candidate_id}"

        return dict(
            slug=slug,
            candidate_id=candidate_id,
            tags=tags,
            names=[
                Name(
                    kind="PRIMARY",
                    en=NameParts(
                        full=self.name_extractor.standardize_name(translated["name"])
                    ),
                    ne=NameParts(
                        full=self.name_extractor.standardize_name(raw["CandidateName"])
                    ),
                ).model_dump()
            ],
            attributes=attributes,
            attributions=[self._build_attribution()],
            personal_details=personal_details.model_dump(),
            identifiers=[self._build_identifier(candidate_id)],
            electoral_details=electoral_details.model_dump(),
            pictures=[self._build_picture(candidate_id)],
        )

    def _build_personal_details(self, raw: dict, translated: dict) -> PersonDetails:
        birth_date = self._parse_dob(raw.get("DOB"))

        citizenship_place = None
        if raw.get("CTZDIST"):
            citizenship_district = self._get_district_id(raw.get("CTZDIST"))
            citizenship_place = Address(location_id=citizenship_district)

        father_en = self._clean_attr(translated.get("father_name"))
        father_ne = self._clean_attr(raw.get("FATHER_NAME"))
        spouse_en = self._clean_attr(translated.get("spouse_name"))
        spouse_ne = self._clean_attr(raw.get("SPOUCE_NAME"))
        addr_en = self._clean_attr(translated.get("address"))
        addr_ne = self._clean_attr(raw.get("ADDRESS"))

        education = self._build_education(raw, translated)
        positions = self._build_positions(raw, translated)

        return PersonDetails(
            birth_date=str(birth_date),
            gender=self._parse_gender(raw.get("Gender", "")),
            father_name=(
                self._build_lang_text(father_en, father_ne, standardize=True)
                if father_en or father_ne
                else None
            ),
            citizenship_place=citizenship_place,
            spouse_name=(
                self._build_lang_text(spouse_en, spouse_ne, standardize=True)
                if spouse_en or spouse_ne
                else None
            ),
            address=Address(description2=self._build_lang_text(addr_en, addr_ne)),
            education=education if education else None,
            positions=positions if positions else None,
        )

    def _build_electoral_details(
        self, candidate_id: int, raw: dict, translated: dict
    ) -> ElectoralDetails:
        party_id = self._get_party_id(
            raw.get("PoliticalPartyName", ""), collect_missing=False
        )
        constituency_id = self._get_constituency_id(raw)
        symbol = self._build_symbol(raw, translated)

        pa_subdivision = None
        if not raw.get("central"):
            pa_subdivision = "A" if raw.get("SCConstID") == 1 else "B"

        candidacy = Candidacy(
            election_year=2079,
            election_type=(
                ElectionType.FEDERAL if raw.get("central") else ElectionType.PROVINCIAL
            ),
            constituency_id=constituency_id,
            pa_subdivision=pa_subdivision,
            position=(
                ElectionPosition.FEDERAL_PARLIAMENT
                if raw.get("central")
                else ElectionPosition.PROVINCIAL_ASSEMBLY
            ),
            candidate_id=candidate_id,
            party_id=party_id,
            votes_received=raw.get("TotalVoteReceived"),
            elected=raw.get("Remarks") == "Elected",
            symbol=symbol,
        )
        return ElectoralDetails(candidacies=[candidacy])

    def _build_symbol(self, raw: dict, translated: dict) -> ElectionSymbol | None:
        if not (raw.get("SymbolID") and raw.get("SymbolName")):
            return None
        symbol_en = self._clean_attr(translated.get("symbol_name"))
        return ElectionSymbol(
            symbol_name=LangText(
                en=(
                    LangTextValue(value=symbol_en, provenance="translation_service")
                    if symbol_en
                    else None
                ),
                ne=LangTextValue(value=raw["SymbolName"], provenance="imported"),
            ),
            nec_id=int(raw["SymbolID"]),
        )

    def _build_attributes(self, raw: dict, translated: dict) -> dict:
        inst_en = self._clean_attr(translated.get("institution"))
        inst_ne = self._clean_attr(raw.get("NAMEOFINST"))
        qual_en = self._clean_attr(translated.get("qualification"))
        qual_ne = self._clean_attr(raw.get("QUALIFICATION"))
        other_en = self._clean_attr(translated.get("other_details"))
        other_ne = self._clean_attr(raw.get("OTHERDETAILS"))

        return {
            "election_council_misc": {
                "institution": (
                    self._build_lang_text(inst_en, inst_ne)
                    if inst_en or inst_ne
                    else None
                ),
                "qualification": (
                    self._build_lang_text(qual_en, qual_ne)
                    if qual_en or qual_ne
                    else None
                ),
                "other_details": (
                    self._build_lang_text(other_en, other_ne)
                    if other_en or other_ne
                    else None
                ),
            }
        }

    def _build_tags(self, raw: dict, candidacy: Candidacy) -> list[str]:
        tags = []
        if raw.get("central"):
            tags.append("federal-election-2079-candidate")
            if candidacy.elected:
                tags.append("federal-election-2079-elected")
        else:
            tags.append("provincial-election-2079-candidate")
            if candidacy.elected:
                tags.append("provincial-election-2079-elected")
        return tags

    def _build_attribution(self) -> Attribution:
        return Attribution(
            title=LangText(
                en=LangTextValue(
                    value="Nepal Election Commission - 2079 results", provenance="human"
                ),
                ne=LangTextValue(
                    value="नेपाल निर्वाचन आयोग - २०७९ को नतिजा", provenance="human"
                ),
            ),
            details=LangText(
                en=LangTextValue(
                    value=f"2079 Election Results - imported {DATE}", provenance="human"
                ),
                ne=LangTextValue(
                    value=f"२०७९ निर्वाचन परिणाम - आयात मिति {DATE} A.D.",
                    provenance="human",
                ),
            ),
        )

    def _build_identifier(self, candidate_id: int) -> ExternalIdentifier:
        return ExternalIdentifier(
            scheme="other",
            name=LangText(
                en=LangTextValue(value="nec_candidate_id", provenance="human"),
                ne=LangTextValue(value="निर्वाचन आयोग दर्ता नं०", provenance="human"),
            ),
            value=str(candidate_id),
        )

    def _build_picture(self, candidate_id: int) -> EntityPicture:
        return EntityPicture(
            type=EntityPictureType.THUMB,
            url=f"https://assets.nes.jawafdehi.org/assets/images/election-commission-2079-pictures/{candidate_id}.jpg",
            description="Source: Nepal Election Commission",
        )

    def _build_education(self, raw: dict, translated: dict) -> list[Education] | None:
        inst_en = self._clean_attr(translated.get("education_institution"))
        inst_ne = self._clean_attr(raw.get("NAMEOFINST"))
        degree_en = self._clean_attr(translated.get("education_level"))
        field_en = self._clean_attr(translated.get("education_field"))

        if not (inst_en or inst_ne or degree_en or field_en):
            return None

        return [
            Education(
                institution=(
                    self._build_lang_text(inst_en, inst_ne)
                    if inst_en or inst_ne
                    else LangText()
                ),
                degree=(
                    self._build_lang_text(degree_en, None, en_provenance="llm")
                    if degree_en
                    else None
                ),
                field=(
                    self._build_lang_text(field_en, None, en_provenance="llm")
                    if field_en
                    else None
                ),
            )
        ]

    def _build_positions(self, raw: dict, translated: dict) -> list[Position] | None:
        title_en = self._clean_attr(translated.get("position_title"))
        org_en = self._clean_attr(translated.get("organization"))
        desc_en = self._clean_attr(translated.get("description"))

        if not (title_en or org_en):
            return None

        return [
            Position(
                title=(
                    self._build_lang_text(title_en, None, en_provenance="llm")
                    if title_en
                    else LangText()
                ),
                organization=(
                    self._build_lang_text(org_en, None, en_provenance="llm")
                    if org_en
                    else None
                ),
                description=desc_en[:200] if desc_en else None,
            )
        ]

    def _build_lang_text(
        self,
        en_val: str | None,
        ne_val: str | None,
        standardize: bool = False,
        en_provenance="translation_service",
        ne_provenance="imported",
    ) -> LangText:
        if standardize:
            en_val = self.name_extractor.standardize_name(en_val) if en_val else None
            ne_val = self.name_extractor.standardize_name(ne_val) if ne_val else None
        return LangText(
            en=(
                LangTextValue(value=en_val, provenance=en_provenance)
                if en_val
                else None
            ),
            ne=(
                LangTextValue(value=ne_val, provenance=ne_provenance)
                if ne_val
                else None
            ),
        )

    @staticmethod
    def _clean_attr(attr: str) -> str | None:
        if not attr:
            return None
        attr = attr.strip()
        if attr == "0" or attr.lower() == "n/a" or attr == "-":
            return None
        # Remove excessive dots (4 or more consecutive dots)
        import re

        attr = re.sub(r"\.{2,}", "", attr)
        attr = attr.strip()
        if not attr:
            return None
        return attr

    @staticmethod
    def _parse_gender(gender_str: str) -> Gender:
        gender_map = {"पुरुष": Gender.MALE, "महिला": Gender.FEMALE}
        return gender_map.get(gender_str, Gender.OTHER)

    @staticmethod
    def _parse_dob(dob_str: str) -> date | None:
        if not dob_str:
            return None
        try:
            parts = dob_str.replace("/", ".").split(".")
            if len(parts) != 3:
                return None
            year, month, day = parts[0].zfill(4), parts[1].zfill(2), parts[2].zfill(2)
            date_bs = f"{year}/{month}/{day}"
            date_ad = converter.bs_to_ad(date_bs)
            y, m, d = date_ad.split("/")
            return date(int(y), int(m), int(d))
        except Exception:
            return None

    async def _verify(self):
        entities = await self.context.db.list_entities(
            limit=10_000, entity_type="person"
        )
        self.context.log(f"Verified: {len(entities)} person entities in database")


async def migrate(context: MigrationContext) -> None:
    migration = CandidateMigration(context)
    await migration.run()
