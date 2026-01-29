# Migration: 010-source-2082-direct-candidates

## Purpose

Import 2082 (2025 AD) direct election candidates as Person entities with electoral details. This migration:
1. Creates/updates political parties for 2082 election
2. Updates existing candidates (from 2079) with new 2082 candidacy
3. Creates new candidate entities for first-time candidates
4. Does NOT include family information (per migration 007 policy)

## Data Sources

- Nepal Election Commission 2082 Election Candidate List
  - `DirectElectionResultCentral2082.json` - Direct/FPTP election candidates
  - `candidate_id_matches_2079_2082.csv` - Mapping of 2079 to 2082 candidate IDs
  - `district-to-slug.csv` - District name to slug mapping
  - `party-updates.json` - Political party updates for 2082
- Source: https://result.election.gov.np/

## Translation Process

This migration follows a two-step pattern:

1. **generate_translations.py** - Translates Nepali candidate data to English
   - Uses Google Vertex AI (Gemini) for structured translation
   - Translates names, addresses, qualifications, and other text fields
   - Does NOT translate family information (father, mother, spouse)
   - Saves translations to `data/translations.json`
   - Supports incremental translation (can resume if interrupted)

2. **migrate.py** - Creates/updates Person entities from translated data
   - Step 1: Creates new political parties and fixes existing party names
   - Step 2: Imports candidates:
     - Loads all existing person entities into memory
     - Matches 2082 candidates to 2079 candidates using ID mapping
     - Updates existing candidates with new 2082 electoral history
     - Creates new person entities for first-time candidates
   - Links candidates to existing political parties
   - Creates bilingual Person entities with electoral details
   - Ensures no slug collisions

## Changes

### Political Parties
- Creates 3 new political parties for 2082 election
- Updates existing party names with corrections

### Person Entities
- Updates existing candidates (from 2079) with 2082 candidacy information
- Creates new Person entities for first-time 2082 candidates
- Each person includes:
  - Primary name in both Nepali and English
  - Personal details: gender, address
  - Age as attribute: "Aged {age} as of January 2026" (not as birth_date)
  - Electoral details: 2082 candidacy information, party affiliation, election symbol
  - Education and position information (when available)
  - External identifier linking to Nepal Election Commission candidate ID
  - Profile picture URL from election commission assets
  - Attribution to Nepal Election Commission
  - Tags: "federal-election-2082-candidate"
- Does NOT include family information (father, mother, spouse names)
- Links candidates to existing political parties
- Election results show null votes (election hasn't happened yet)

## Conflict Resolution Process

This migration implements a sophisticated conflict resolution strategy to handle candidates who ran in both 2079 and 2082 elections:

### 1. Candidate Matching Strategy

The migration uses a three-step matching process:

1. **Load ID Mapping**: Reads `candidate_id_matches_2079_2082.csv` which maps 2082 candidate IDs to their 2079 counterparts
2. **Build NEC ID Lookup**: Creates an in-memory index of all existing person entities by their Nepal Election Commission (NEC) candidate ID
3. **Match Candidates**: For each 2082 candidate:
   - Checks if they have a 2079 ID in the mapping file
   - Looks up the person entity using the 2079 NEC ID
   - If found → **UPDATE** existing entity
   - If not found → **CREATE** new entity

### 2. Update Strategy (Existing Candidates)

For candidates who ran in both elections:

- **Preserves existing data**: Name, personal details, 2079 electoral history remain unchanged
- **Appends new candidacy**: Adds 2082 election information to `electoral_details.candidacies[]` array
- **Updates tags**: Adds "federal-election-2082-candidate" tag if not present
- **No collision risk**: Uses existing entity ID, no slug conflicts possible

Example:
```python
# Candidate ran in 2079 (ID: 12345) and 2082 (ID: 67890)
# Entity already exists with ID: entity:person/ram-bahadur-thapa
# Migration adds new candidacy to existing entity:
person.electoral_details.candidacies.append(
    Candidacy(election_year=2082, candidate_id=67890, ...)
)
```

### 3. Creation Strategy (New Candidates)

For first-time candidates in 2082:

- **Slug generation**: Creates slug from English name using `text_to_slug()`
- **Collision detection**: Checks if slug already exists in database
- **Collision resolution**: If slug exists, appends candidate ID: `{slug}-{candidate_id}`
- **Batch creation**: Uses Publication Service to create all new entities

Example collision resolution:
```python
# Original slug: "ram-bahadur-thapa"
# If exists → "ram-bahadur-thapa-67890"
```

### 4. Why This Approach?

**Advantages:**
- **Data continuity**: Candidates maintain single entity across elections
- **Historical tracking**: Full electoral history in one place
- **No duplicates**: Matching prevents creating duplicate entities for same person
- **Graceful degradation**: If matching fails, creates new entity (safe fallback)

**Trade-offs:**
- **Requires ID mapping**: Depends on `candidate_id_matches_2079_2082.csv` accuracy
- **Memory intensive**: Loads all person entities into memory for matching
- **Manual mapping**: ID matching file must be created/maintained manually

### 5. Conflict Resolution Edge Cases

**Case 1: Candidate ID mismatch**
- If 2082 candidate has 2079 ID in mapping but no matching entity exists
- Resolution: Creates new entity (treats as first-time candidate)

**Case 2: Name slug collision**
- If new candidate's name slug matches existing entity
- Resolution: Appends candidate ID to slug

**Case 3: Missing translation**
- If candidate has no translation in `translations.json`
- Resolution: Skips candidate with warning log

**Case 4: Party not found**
- If candidate's party not in database or mapping
- Resolution: Raises exception (migration fails, must fix data)

## Notes

- Age is stored as an attribute ("Aged {age} as of January 2026"), not as birth_date
- Birth dates are NOT set (no approximation from age)
- Gender is parsed from Nepali text ("पुरुष" = MALE, "महिला" = FEMALE)
- Party linking uses cleaned party names (removes "(एकल चुनाव चिन्ह)" suffix)
- Address data is stored as bilingual description
- Translation uses Gemini 2.5 Flash for structured data extraction
- Duplicate name slugs resolved by appending candidate ID
- Family information is NOT collected per migration 007 policy
- Processing time: ~2-3 hours for full translation (depending on API rate limits)
- Migration execution: ~10-15 seconds for entity creation/updates
- Votes received is set to None (election hasn't happened yet)

## Testing

Run translation first:
```bash
cd services/NepalEntityService
poetry run python migrations/010-source-2082-direct-candidates/generate_translations.py
```

Then run migration:
```bash
poetry run nes migrate run 010-source-2082-direct-candidates --dry-run
```

Verify:
- Check that `data/translations.json` is created with 3,406 translations
- Verify existing candidates are updated with 2082 candidacy
- Verify new candidates are created as person entities
- Check that candidates are linked to political parties via electoral_details.candidacies[0].party_id
- Review sample entities to ensure bilingual data quality
- Confirm tags are applied correctly ("federal-election-2082-candidate")
- Validate external identifiers and picture URLs are set
- Ensure no family information is present in any entities

## Rollback

- Use Git revert on the database repository commit
- Manually delete created Person entities using the Publication Service
- Manually revert updates to existing Person entities
- Translation file (`data/translations.json`) can be regenerated if needed

## Dependencies

- Migration 003: Political parties must exist
- Migration 005: 2079 candidates (for matching existing candidates)
- Migration 007: Family information redaction policy
