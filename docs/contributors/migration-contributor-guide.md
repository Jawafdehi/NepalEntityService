# Migration Contributor Guide

This guide is for community members who want to contribute data updates to the Nepal Entity Service through the migration system. You'll learn how to create migrations, test them locally, and submit them for review.

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Creating a Migration](#creating-a-migration)
4. [Migration Script API](#migration-script-api)
5. [Common Patterns](#common-patterns)
6. [Testing Locally](#testing-locally)
7. [Submitting Your Migration](#submitting-your-migration)
8. [Best Practices](#best-practices)
9. [Examples](#examples)

---

## Introduction

### What is a Migration?

A migration is a versioned folder containing:
- **migrate.py**: Python script that performs data changes
- **README.md**: Documentation of the migration purpose and approach
- **Data files**: CSV, Excel, JSON files with source data (optional)
- **Supporting files**: Any additional files needed (optional)

Migrations are executed sequentially and tracked through Git commits in the Database Repository. Each migration creates a permanent snapshot of the database state.

### Who Can Contribute?

Anyone can contribute migrations! Common contributors include:
- Researchers with curated datasets
- Data enthusiasts improving data quality
- Developers building data import tools
- Community members fixing errors or adding missing information

### What You'll Learn

- How to create a migration folder
- How to write migration scripts
- How to test migrations locally
- How to submit migrations via GitHub pull requests
- Best practices for data contributions

---

## Getting Started

### Prerequisites

1. **Python 3.11+** installed
2. **Git** installed
3. **Poetry** for dependency management
4. **GitHub account** for submitting pull requests

### Fork and Clone the Repository

```bash
# Fork the repository on GitHub
# https://github.com/Jawafdehi/NepalEntityService

# Clone your fork
git clone https://github.com/YOUR_USERNAME/NepalEntityService.git
cd NepalEntityService

# Add upstream remote
git remote add upstream https://github.com/Jawafdehi/NepalEntityService.git
```

### Install Dependencies

```bash
# Install project dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Initialize Database Submodule

```bash
# Initialize the database submodule
git submodule init
git submodule update

# The database will be at nes-db/
```

---

## Creating a Migration

### Step 1: Create Migration Folder

Use the CLI command to generate a migration from the template:

```bash
nes migration create "add-new-ministers"
```

This creates:
```
migrations/NNN-add-new-ministers/
├── migrate.py      # Pre-filled template
└── README.md       # Documentation template
```

The system automatically assigns the next available prefix number (e.g., 005).

### Step 2: Add Your Data Files

Copy your data files into the migration folder:

```bash
cp ~/ministers.csv migrations/005-add-new-ministers/
```

Your migration folder now looks like:
```
migrations/005-add-new-ministers/
├── migrate.py
├── README.md
└── ministers.csv
```

### Step 3: Update README.md

Document your migration:

```markdown
# Migration: 005-add-new-ministers

## Purpose
Import current cabinet ministers from the 2024 government formation.

## Data Sources
- Nepal Government Official Website: https://opmcm.gov.np/
- Cabinet list published on 2024-03-15

## Changes
- Creates 25 person entities for new ministers
- Creates HOLDS_POSITION relationships to government bodies
- Updates existing entities if ministers were already in database

## Dependencies
Requires government body entities to exist (created in migration 003)

## Notes
Data verified against official government records as of 2024-03-15.
```

### Step 4: Write Migration Script

Edit `migrate.py` to implement your data changes. See [Migration Script API](#migration-script-api) below.

---

## Migration Script API

### Script Structure

Every migration script must:
1. Define metadata constants (AUTHOR, DATE, DESCRIPTION)
2. Implement an async `migrate(context)` function

```python
"""
Migration: 005-add-new-ministers
Description: Import current cabinet ministers
Author: contributor@example.com
Date: 2024-03-15
"""

# Migration metadata
AUTHOR = "contributor@example.com"
DATE = "2024-03-15"
DESCRIPTION = "Import current cabinet ministers from official records"

async def migrate(context):
    """
    Main migration function.
    
    Args:
        context: MigrationContext with access to services and data
    """
    # Your migration logic here
    context.log("Migration completed")
```

### Context Object

The `context` object provides access to services and utilities:

#### Service Access

```python
# Publication Service - create/update entities and relationships
await context.publication.create_entity(entity, author_id, change_description)
await context.publication.update_entity(entity, author_id, change_description)
await context.publication.create_relationship(source_id, target_id, type, author_id, change_description)

# Search Service - query existing entities
entity = await context.search.find_entity_by_name("Ram Sharma", "person")
results = await context.search.search_entities(query="Nepal", entity_type="organization")

# Scraping Service - normalize and translate data
normalized = await context.scraping.normalize_name("राम शर्मा", language="ne")

# Database - direct read access
entity = await context.db.get_entity("entity:person/ram-sharma")
```

#### File Reading Helpers

```python
# Read CSV file from migration folder
data = context.read_csv("ministers.csv")
# Returns: List[Dict[str, Any]]

# Read JSON file
data = context.read_json("parties.json")
# Returns: Any (dict, list, etc.)

# Read Excel file
data = context.read_excel("data.xlsx", sheet_name="Sheet1")
# Returns: List[Dict[str, Any]]
```

#### Migration Folder Path

```python
# Access migration folder path
migration_dir = context.migration_dir
# Returns: Path object

# Read custom files
with open(context.migration_dir / "custom.txt") as f:
    content = f.read()
```

#### Logging

```python
# Log progress messages
context.log("Processing 100 entities...")
context.log(f"Created {count} entities")
```

### Creating Entities

```python
from nes.core.models.entity import Entity, EntityType
from nes.core.models.name import Name, NameKind, NameParts

# Create author ID for this migration
author_id = "author:migration:005-add-new-ministers"

# Build entity
entity_data = {
    "slug": "ram-sharma",
    "type": "person",
    "sub_type": "politician",
    "names": [
        {
            "kind": "PRIMARY",
            "en": {"full": "Ram Sharma"},
            "ne": {"full": "राम शर्मा"}
        }
    ],
    "attributes": {
        "position": "Minister of Finance"
    }
}

# Create entity
await context.publication.create_entity(
    entity_data=entity_data,
    author_id=author_id,
    change_description="Import minister from official records"
)
```

### Updating Entities

```python
# Find existing entity
entity = await context.search.find_entity_by_name("Ram Sharma", "person")

if entity:
    # Update attributes
    if not entity.attributes:
        entity.attributes = {}
    entity.attributes["position"] = "Minister of Finance"
    entity.attributes["term_start"] = "2024-03-15"
    
    # Save update
    await context.publication.update_entity(
        entity=entity,
        author_id=author_id,
        change_description="Updated ministerial position"
    )
```

### Creating Relationships

```python
# Create relationship between person and organization
await context.publication.create_relationship(
    source_entity_id="entity:person/ram-sharma",
    target_entity_id="entity:organization/government_body/ministry-of-finance",
    relationship_type="HOLDS_POSITION",
    start_date=date(2024, 3, 15),
    attributes={
        "position": "Minister",
        "appointment_type": "Cabinet"
    },
    author_id=author_id,
    change_description="Added ministerial appointment"
)
```

---

## Common Patterns

### Pattern 1: Import from CSV

```python
async def migrate(context):
    """Import entities from CSV file."""
    # Read CSV
    rows = context.read_csv("data.csv")
    
    author_id = "author:migration:005-import-data"
    
    for row in rows:
        entity_data = {
            "slug": row["slug"],
            "type": row["type"],
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {"full": row["name_en"]},
                    "ne": {"full": row["name_ne"]}
                }
            ],
            "attributes": {
                "source": row.get("source", "")
            }
        }
        
        await context.publication.create_entity(
            entity_data=entity_data,
            author_id=author_id,
            change_description=f"Import {row['name_en']}"
        )
    
    context.log(f"Imported {len(rows)} entities")
```

### Pattern 2: Update Existing Entities

```python
async def migrate(context):
    """Update attributes for existing entities."""
    # Read update data
    updates = context.read_json("updates.json")
    
    author_id = "author:migration:006-update-attributes"
    
    for update in updates:
        # Find entity
        entity = await context.db.get_entity(update["entity_id"])
        
        if not entity:
            context.log(f"Entity not found: {update['entity_id']}")
            continue
        
        # Apply updates
        if not entity.attributes:
            entity.attributes = {}
        entity.attributes.update(update["new_attributes"])
        
        # Save
        await context.publication.update_entity(
            entity=entity,
            author_id=author_id,
            change_description=update["description"]
        )
    
    context.log(f"Updated {len(updates)} entities")
```

### Pattern 3: Create Entities with Relationships

```python
async def migrate(context):
    """Create entities and their relationships."""
    data = context.read_csv("politicians.csv")
    
    author_id = "author:migration:007-politicians-with-parties"
    
    for row in data:
        # Create person entity
        person_data = {
            "slug": row["slug"],
            "type": "person",
            "sub_type": "politician",
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {"full": row["name_en"]},
                    "ne": {"full": row["name_ne"]}
                }
            ]
        }
        
        person = await context.publication.create_entity(
            entity_data=person_data,
            author_id=author_id,
            change_description=f"Import politician {row['name_en']}"
        )
        
        # Create party membership
        if row.get("party_id"):
            await context.publication.create_relationship(
                source_entity_id=person.id,
                target_entity_id=row["party_id"],
                relationship_type="MEMBER_OF",
                author_id=author_id,
                change_description="Add party membership"
            )
    
    context.log(f"Created {len(data)} politicians with relationships")
```

### Pattern 4: Conditional Create or Update

```python
async def migrate(context):
    """Create new entities or update existing ones."""
    data = context.read_csv("entities.csv")
    
    author_id = "author:migration:008-upsert-entities"
    created = 0
    updated = 0
    
    for row in data:
        # Check if entity exists
        entity = await context.search.find_entity_by_name(
            row["name_en"],
            row["type"]
        )
        
        if entity:
            # Update existing
            entity.attributes = entity.attributes or {}
            entity.attributes.update(row.get("attributes", {}))
            
            await context.publication.update_entity(
                entity=entity,
                author_id=author_id,
                change_description="Update from new data source"
            )
            updated += 1
        else:
            # Create new
            entity_data = {
                "slug": row["slug"],
                "type": row["type"],
                "names": [
                    {
                        "kind": "PRIMARY",
                        "en": {"full": row["name_en"]},
                        "ne": {"full": row["name_ne"]}
                    }
                ],
                "attributes": row.get("attributes", {})
            }
            
            await context.publication.create_entity(
                entity_data=entity_data,
                author_id=author_id,
                change_description="Create from new data source"
            )
            created += 1
    
    context.log(f"Created {created}, updated {updated} entities")
```

### Pattern 5: Error Handling

```python
async def migrate(context):
    """Import with error handling and reporting."""
    data = context.read_csv("data.csv")
    
    author_id = "author:migration:009-safe-import"
    stats = {"success": 0, "failed": 0, "errors": []}
    
    for row in data:
        try:
            entity_data = {
                "slug": row["slug"],
                "type": row["type"],
                "names": [
                    {
                        "kind": "PRIMARY",
                        "en": {"full": row["name_en"]},
                        "ne": {"full": row["name_ne"]}
                    }
                ]
            }
            
            await context.publication.create_entity(
                entity_data=entity_data,
                author_id=author_id,
                change_description="Import entity"
            )
            stats["success"] += 1
            
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append({
                "slug": row.get("slug", "unknown"),
                "error": str(e)
            })
            context.log(f"Failed to import {row.get('slug')}: {e}")
    
    context.log(f"Success: {stats['success']}, Failed: {stats['failed']}")
    
    if stats["errors"]:
        context.log("Errors:")
        for error in stats["errors"]:
            context.log(f"  - {error['slug']}: {error['error']}")
```

---

## Testing Locally

### Step 1: List Migrations

```bash
# See all migrations
nes migration list

# See pending migrations
nes migration list --pending
```

### Step 2: Run Your Migration

```bash
# Run specific migration
nes migration run 005-add-new-ministers

# Note: Migration will create logs and modify database
# You'll need to commit changes manually afterward
```

### Step 3: Verify Results

```python
# Use Python to verify entities were created
from nes.database.file_database import FileDatabase
from nes.services.search import SearchService

db = FileDatabase(base_path="nes-db/v2")
search = SearchService(database=db)

# Search for created entities
results = await search.search_entities(
    query="minister",
    entity_type="person"
)

for entity in results:
    print(f"✓ {entity.names[0].en.full}")
```

### Step 4: Check Git Status

```bash
# See what files changed in database
cd nes-db
git status
git diff

# See commit created by migration
git log -1
```

### Step 5: Test Idempotency

```bash
# Run migration again - should skip (already applied)
nes migration run 005-add-new-ministers

# Output should show: "Migration already applied, skipping"
```

---

## Submitting Your Migration

### Step 1: Commit Your Migration

```bash
# In main repository (not nes-db)
git add migrations/005-add-new-ministers/
git commit -m "Add migration: 005-add-new-ministers

Import current cabinet ministers from official government records.
Adds 25 person entities and HOLDS_POSITION relationships."
```

### Step 2: Push to Your Fork

```bash
git push origin main
```

### Step 3: Create Pull Request

1. Go to your fork on GitHub
2. Click "New Pull Request"
3. Fill in the PR template:

```markdown
## Migration: 005-add-new-ministers

### Purpose
Import current cabinet ministers from the 2024 government formation.

### Data Sources
- Nepal Government Official Website: https://opmcm.gov.np/
- Cabinet list published on 2024-03-15

### Changes
- Creates 25 person entities for new ministers
- Creates HOLDS_POSITION relationships to government bodies
- Updates existing entities if ministers were already in database

### Testing
- [x] Tested locally with `nes migration run`
- [x] Verified entities created correctly
- [x] Tested idempotency (re-running skips execution)
- [x] Checked data quality

### Checklist
- [x] README.md documents the migration
- [x] Data sources are cited
- [x] Migration script includes error handling
- [x] Tested locally
- [x] Follows naming conventions
```

### Step 4: Wait for Review

Maintainers will:
1. Review your migration code
2. Check data quality
3. Verify data sources
4. Test the migration
5. Provide feedback or approve

### Step 5: Address Feedback

If changes are requested:

```bash
# Make changes to your migration
vim migrations/005-add-new-ministers/migrate.py

# Commit changes
git add migrations/005-add-new-ministers/
git commit -m "Address review feedback: improve error handling"

# Push updates
git push origin main
```

---

## Best Practices

### 1. Document Data Sources

Always cite your data sources in README.md:

```markdown
## Data Sources
- Nepal Government Official Website: https://opmcm.gov.np/
- Election Commission: https://election.gov.np/
- Wikipedia: https://en.wikipedia.org/wiki/...
- Verified on: 2024-03-15
```

### 2. Use Descriptive Migration Names

```bash
# Good
005-add-cabinet-ministers-2024
006-update-party-leadership
007-import-election-results-2022

# Bad
005-update
006-fix
007-data
```

### 3. Include Both English and Nepali Names

```python
"names": [
    {
        "kind": "PRIMARY",
        "en": {"full": "Ram Chandra Poudel"},
        "ne": {"full": "राम चन्द्र पौडेल"}
    }
]
```

### 4. Handle Errors Gracefully

```python
try:
    await context.publication.create_entity(...)
except Exception as e:
    context.log(f"Failed to create entity: {e}")
    # Continue with next entity instead of crashing
```

### 5. Log Progress

```python
context.log(f"Processing {len(data)} entities...")
context.log(f"Created {created} entities")
context.log(f"Updated {updated} entities")
context.log("Migration completed successfully")
```

### 6. Test Idempotency

Ensure your migration can be run multiple times safely:

```python
# Check if entity exists before creating
entity = await context.search.find_entity_by_name(name, type)
if not entity:
    # Create only if doesn't exist
    await context.publication.create_entity(...)
```

### 7. Keep Migrations Focused

Each migration should have a single, clear purpose:
- ✓ Import cabinet ministers
- ✓ Update party leadership
- ✗ Import ministers, update parties, fix typos, add relationships (too much)

### 8. Use Meaningful Author IDs

```python
# Good
author_id = "author:migration:005-add-cabinet-ministers"

# Bad
author_id = "author:migration"
author_id = "author:user"
```

---

## Examples

### Example 1: Simple CSV Import

**File: migrations/010-import-districts/districts.csv**
```csv
slug,name_en,name_ne,province,area_km2
kathmandu,Kathmandu,काठमाडौं,Bagmati,395
lalitpur,Lalitpur,ललितपुर,Bagmati,385
```

**File: migrations/010-import-districts/migrate.py**
```python
"""
Migration: 010-import-districts
Description: Import district data
Author: contributor@example.com
Date: 2024-03-15
"""

AUTHOR = "contributor@example.com"
DATE = "2024-03-15"
DESCRIPTION = "Import district data from official records"

async def migrate(context):
    """Import districts from CSV."""
    districts = context.read_csv("districts.csv")
    
    author_id = "author:migration:010-import-districts"
    
    for district in districts:
        entity_data = {
            "slug": district["slug"],
            "type": "location",
            "sub_type": "district",
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {"full": district["name_en"]},
                    "ne": {"full": district["name_ne"]}
                }
            ],
            "attributes": {
                "province": district["province"],
                "area_km2": float(district["area_km2"])
            }
        }
        
        await context.publication.create_entity(
            entity_data=entity_data,
            author_id=author_id,
            change_description=f"Import district {district['name_en']}"
        )
    
    context.log(f"Imported {len(districts)} districts")
```

### Example 2: Update with Relationships

**File: migrations/011-add-party-memberships/migrate.py**
```python
"""
Migration: 011-add-party-memberships
Description: Add party membership relationships for politicians
Author: contributor@example.com
Date: 2024-03-15
"""

AUTHOR = "contributor@example.com"
DATE = "2024-03-15"
DESCRIPTION = "Add party membership relationships"

from datetime import date

async def migrate(context):
    """Add party memberships."""
    memberships = context.read_csv("memberships.csv")
    
    author_id = "author:migration:011-add-party-memberships"
    created = 0
    
    for row in memberships:
        try:
            await context.publication.create_relationship(
                source_entity_id=row["person_id"],
                target_entity_id=row["party_id"],
                relationship_type="MEMBER_OF",
                start_date=date.fromisoformat(row["start_date"]),
                attributes={
                    "role": row.get("role", "Member")
                },
                author_id=author_id,
                change_description=f"Add party membership"
            )
            created += 1
        except Exception as e:
            context.log(f"Failed to create relationship: {e}")
    
    context.log(f"Created {created} party memberships")
```

---

## Additional Resources

- **Maintainer Guide**: See [Migration Maintainer Guide](/contributors/migration-maintainer-guide) for the review process
- **Architecture**: See [Migration Architecture](/contributors/migration-architecture) for system design
- **API Reference**: See [OpenAPI documentation](/docs) for complete API documentation
- **Examples**: See `examples/` directory for more code examples

---

## Support

For questions or issues:

1. Check this guide and other documentation
2. Review existing migrations in `migrations/` directory
3. Ask in GitHub Discussions
4. Open an issue for bugs or unclear documentation

---

**Last Updated:** 2024
**Version:** 2.0
