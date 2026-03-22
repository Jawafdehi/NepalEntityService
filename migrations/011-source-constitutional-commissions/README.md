# Migration 011: Source Constitutional Commissions

## Overview

This migration imports 108 constitutional commissions and government bodies into NES with proper 4-depth entity prefixes.

## What This Migration Does

- Imports 108 constitutional commission entities
- Introduces 4-depth entity prefixes for better hierarchical organization
- Covers federal, provincial, regional, and district-level constitutional bodies

## Entity Breakdown

| Prefix | Count | Description |
|--------|-------|-------------|
| `organization/government/commission/federal` | 9 | Central constitutional commissions (CIAA, Election Commission, NHRC, etc.) |
| `organization/government/commission/province` | 14 | Provincial offices (7 NHRC + 7 Province Public Service Commissions) |
| `organization/government/commission/regional` | 8 | CIAA regional offices (predates 7-province structure) |
| `organization/government/commission/district` | 77 | District Election Offices (one per district) |
| **Total** | **108** | |

## Data Source

The data was compiled from official sources:
- Commission for the Investigation of Abuse of Authority (CIAA): https://ciaa.gov.np
- Election Commission of Nepal: https://election.gov.np
- National Human Rights Commission (NHRC): https://nhrcnepal.org
- Province Public Service Commissions: Various provincial government websites

## Why 4-Depth Prefixes?

Previously, all government bodies used the 3-depth prefix `organization/government_body`. This migration introduces a more granular classification system:

```
organization/government/commission/federal    ← Central commissions
organization/government/commission/province   ← Provincial offices
organization/government/commission/regional   ← Regional offices (CIAA)
organization/government/commission/district   ← District-level offices
```

This allows for:
- Better organization and filtering of entities
- Clearer hierarchical relationships
- More precise entity type identification

## Prerequisites

Before running this migration, ensure:
1. `MAX_PREFIX_DEPTH` in `nes/core/constraints.py` is set to 4
2. The 4 new prefixes are registered in `nes/core/models/entity_type_map.py`

## Running the Migration

```bash
cd services/nes
poetry run python -m nes.services.migration.runner 011-source-constitutional-commissions
```

## Verification

After running the migration, verify:
- 108 entities created
- Correct prefix distribution (9 federal, 14 province, 8 regional, 77 district)
- All entities have proper bilingual names (English and Nepali)
- Contact information and addresses are properly formatted

## Notes

- CIAA has 8 regional offices (not 7) because its regional structure predates the 2015 federal restructure
- District Election Offices cover all 77 districts of Nepal
- All entities include bilingual content (English and Nepali)
- This migration is for documentation and historical record; production entities go through NES Queue via Jawafdehi API

## Author

Kushal KC - 2026-03-22
