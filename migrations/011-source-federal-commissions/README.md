# Migration 011: Provincial Public Service Commissions

## Overview

This migration imports Nepal's 7 Provincial Public Service Commissions (PPSCs) as government body entities into the NES database. These constitutional bodies are responsible for recruiting provincial and local government employees through merit-based competitive examinations.

## Data Source

- **Primary Sources**: Official PPSC websites and collegenp.com
- **Data Collection Date**: March 2026
- **Author**: Kushal KC
- **Verification**: All contact information, addresses, and establishment dates verified from official sources

## Entities Created

This migration creates 7 government body entities representing the Provincial Public Service Commissions:

1. **Koshi Province PSC** - Biratnagar (Established: 2020-02-02)
2. **Madhesh Province PSC** - Janakpur (Established: 2019-08-21)
3. **Bagmati Province PSC** - Hetauda (Established: 2019-11-04)
4. **Gandaki Province PSC** - Pokhara (Established: 2021-03-24)
5. **Lumbini Province PSC** - Butwal (Established: 2019-09-13)
6. **Karnali Province PSC** - Birendranagar, Ward 8 (Established: 2019)
7. **Sudurpashchim Province PSC** - Dhangadhi (Established: 2021-04-02)

## Data Fields

Each PPSC entity includes:

### Core Information
- **Slug**: Unique identifier (e.g., `psc-koshi-provincial-office`)
- **Names**: Bilingual (English and Nepali) official names
- **Entity Type**: Organization → Government Body
- **Government Type**: Provincial

### Location Data
- **Address**: Full bilingual address with location linking
- **Location ID**: Linked to ward/municipality/province in database
- **Location Fallback Strategy**: Ward → Municipality → Province

### Contact Information
- **Phones**: Multiple contact numbers (standardized format without country code)
- **Email**: Official email addresses
- **Website**: Official government websites

### Descriptions
- **Short Description**: One-line summary of the commission's role
- **Description**: Detailed explanation of constitutional mandate, responsibilities, and civic importance

### Metadata
- **Tags**: `["provincial-psc", "provincial-government"]`
- **Attributes**: Establishment date
- **Established**: Date when the commission was officially established

## Migration Process

The migration follows a 3-stage process:

### Stage 1: Data Preparation
- Load source data from `source/provincial_psc_offices.json`
- Build location lookups for all wards, municipalities, and provinces
- Construct entity data structures with all required fields
- Validate bilingual content (English and Nepali)

### Stage 2: Duplicate Detection
- Check for existing entities by slug, English name, and Nepali name
- Identify duplicates within migration data
- Separate entities into "to create" and "to skip" lists
- Log all duplicate detection results

### Stage 3: Entity Creation
- Create new government body entities in the database
- Skip entities that already exist
- Log creation results and final counts
- Verify total entity count after migration

## Location Linking Strategy

The migration uses a fallback strategy to link PSC offices to the most specific location available:

1. **Ward Level** (if ward_number provided):
   - Pattern: `{municipality-slug} - ward {number}`
   - Example: `birendranagar-municipality - ward 8`

2. **Municipality Level** (fallback):
   - Uses municipality English name
   - Example: `Biratnagar Metropolitan City`

3. **Province Level** (final fallback):
   - Uses province English name
   - Example: `Koshi Province`

**Note**: Only Karnali PSC has ward-level precision (Ward 8). Others link to municipality level.

## Data Quality Assurance

### Completeness Checks
- ✅ All 7 provinces covered
- ✅ All entities have bilingual names
- ✅ All entities have bilingual descriptions (short and long)
- ✅ All entities have bilingual addresses
- ✅ All entities have contact information (phones, email, website)
- ✅ All entities have establishment dates
- ✅ All entities have location linking

### Consistency Checks
- ✅ Phone number format standardized (no country code prefix)
- ✅ Email addresses verified from official sources
- ✅ Website URLs verified and accessible
- ✅ Slug naming convention consistent
- ✅ Tags consistent across all entities

### Validation
- ✅ No duplicate slugs in source data
- ✅ No duplicate names in source data
- ✅ All required fields present
- ✅ JSON syntax valid
- ✅ Nepali Unicode characters properly encoded

## Running the Migration

```bash
# Run the migration
poetry run nes migration run 011-source-federal-commissions

# Verify the migration
poetry run nes migration status
```

## Expected Output

```
Migration started: Importing 7 Provincial PSC offices
Created author: Kushal KC (...)
Loaded 7 provincial PSC offices from source data
Building location lookups...
Built location lookups: XXXX entries
Stage 1: Building PSC office data structures...
Stage 1 complete: Prepared 7 PSC offices
Stage 2: Checking for duplicates...
Found XXX existing government_body entities in database
Stage 2 complete: 7 new PSC offices to create, 0 already exist
Stage 3: Creating entities in database...
Created PSC office XXX: Province Public Service Commission, Koshi Province (प्रदेश लोक सेवा आयोग, कोशी प्रदेश)
...
Stage 3 complete: Created 7 provincial PSC offices, skipped 0 duplicates
Final verification: XXX total government_body entities in database
Migration completed successfully
```

## Rollback

If needed, entities can be removed by:
1. Identifying entity IDs from migration logs
2. Using the database deletion tools
3. Or re-running migration with duplicate detection (will skip existing)

## Notes

- This migration is idempotent - running it multiple times will not create duplicates
- Location linking depends on existing location entities in the database
- If locations are not found, location_id will be None (logged in migration output)
- All data sourced from official government websites and verified educational platforms

## References

- Constitution of Nepal, Article 267 (Provincial Public Service Commission)
- Official PPSC websites (psc.koshi.gov.np, ppsc.madhesh.gov.np, etc.)
- CollegeNP.com (verified educational platform)
