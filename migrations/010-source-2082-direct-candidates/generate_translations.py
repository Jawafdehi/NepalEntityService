"""
Script to generate translations.json by translating Nepali candidate data to English.

This script reads the 2082 election JSON data and uses Google Vertex AI to translate
candidate information from Nepali to English using structured data extraction.

Note: This migration does NOT include personal family information (father, spouse, mother)
as per migration 007-redact-family-info policy.
"""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

from nes.services.scraping.providers.google import GoogleVertexAIProvider


class CandidateTranslation(BaseModel):
    """Pydantic model for candidate translation (2082 - no family info)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Candidate name in English")
    address: str = Field(description="Address in English")
    party_name: str = Field(description="Political party name in English")
    experience: str = Field(description="Candidate's experience in English")
    qualification: str = Field(description="Candidate's qualification in English")
    other_details: str = Field(description="Other details in English")
    symbol_name: str = Field(description="Election symbol name in English")
    education_level: str = Field(
        default="",
        description="Candidate's normalized education in English. Should be one of PhD, Masters, Bachelor, Intermediate, SLC, PCL, Diploma, UnderSLC, Literate, Other. Should be mapped from QUALIFICATION and NAMEOFINST fields.",
    )
    education_institution: str = Field(
        default="",
        description="Candidate's normalized education institution in English. Should be mapped from QUALIFICATION and NAMEOFINST fields.",
    )
    education_field: str = Field(
        default="",
        description="Candidate's normalized education field in English (e.g. Law, Civil Engineering, etc.). Should be mapped from QUALIFICATION, EXPERIENCE, and NAMEOFINST fields.",
    )
    position_title: str = Field(
        default="", description="Candidate's position title in English"
    )
    organization: str = Field(
        default="", description="Organization or company name in English"
    )
    description: str = Field(default="", description="Other information in English")


INSTRUCTIONS = """
You are a translation system converting Nepali election candidate information to English.
Translate all text fields to English while preserving proper names accurately.
If a field is empty, use an empty string.
DO NOT include or translate family information (father, mother, spouse names) as this is not collected.
"""


async def translate_candidate(
    provider: GoogleVertexAIProvider, candidate: dict
) -> dict:
    """Translate a single candidate's data from Nepali to English."""

    # Clean party name - remove "(एकल चुनाव चिन्ह)" suffix
    party_name = candidate.get("PoliticalPartyName", "")
    if party_name:
        party_name = party_name.replace("(एकल चुनाव चिन्ह)", "").strip()

    # Helper to convert None to empty string
    def safe_str(value):
        return value if value is not None else ""

    # Create input model (NO family information)
    candidate_data = CandidateTranslation(
        name=safe_str(candidate.get("CandidateName", "")),
        address=safe_str(candidate.get("ADDRESS", "")),
        party_name=safe_str(party_name),
        experience=safe_str(candidate.get("EXPERIENCE", "")),
        qualification=safe_str(candidate.get("QUALIFICATION", "")),
        other_details=safe_str(candidate.get("OTHERDETAILS", "")),
        symbol_name=safe_str(candidate.get("SymbolName", "")),
    ).model_dump()

    candidate_data["experience"] = safe_str(candidate.get("EXPERIENCE"))
    candidate_data["qualification"] = safe_str(candidate.get("QUALIFICATION"))
    candidate_data["other_details"] = safe_str(candidate.get("OTHERDETAILS"))
    candidate_data["institution_name"] = safe_str(candidate.get("NAMEOFINST"))

    # Extract structured translation
    result = await provider.extract_structured_data(
        f"Translate this: {candidate_data}",
        CandidateTranslation.model_json_schema(),
        instructions=INSTRUCTIONS,
    )

    return result


async def main():
    """Main function to generate translations."""
    # Load environment variables
    load_dotenv()

    # Get script directory
    script_dir = Path(__file__).parent / "data"

    # Initialize AI provider
    project_id = os.environ.get("NES_PROJECT_ID")
    if not project_id:
        raise ValueError("NES_PROJECT_ID environment variable not set")

    provider = GoogleVertexAIProvider(
        project_id=project_id,
        model_id="gemini-2.5-flash",
        temperature=0.3,
    )

    print("Loading raw candidate data...")

    # Read raw JSON file (2082 direct election only)
    with open(
        script_dir / "DirectElectionResultCentral2082.json", "r", encoding="utf-8-sig"
    ) as f:
        all_candidates = json.load(f)

    print(f"Found {len(all_candidates)} candidates to translate")

    # Load existing translations if any
    output_file = script_dir / "translations.json"
    translations = {}
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            translations = json.load(f)
        print(f"Loaded {len(translations)} existing translations")

    # Translate each candidate
    for i, candidate in enumerate(all_candidates, 1):
        candidate_id = str(candidate["CandidateID"])

        if candidate_id in translations:
            print(
                f"[{i}/{len(all_candidates)}] Skipping (already translated): {candidate['CandidateName']}"
            )
            continue

        print(f"[{i}/{len(all_candidates)}] Translating: {candidate['CandidateName']}")
        translated = await translate_candidate(provider, candidate)
        translations[candidate_id] = translated
        print(f"  ✓ {translated.get('name', 'N/A')}")

        # Save after each translation
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Completed: {len(translations)} translations in {output_file}")

    # Print token usage
    usage = provider.get_token_usage()
    print(f"\nToken usage:")
    print(f"  Input:  {usage['input_tokens']:,}")
    print(f"  Output: {usage['output_tokens']:,}")
    print(f"  Total:  {usage['total_tokens']:,}")


if __name__ == "__main__":
    asyncio.run(main())
