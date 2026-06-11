# Migrations Directory

This directory contains versioned migration folders for managing database evolution in the Nepal Entity Service.

## Overview

Migrations are a way to systematically update the database content through versioned, reviewable, and reproducible scripts. Each migration is a folder containing:
- A Python script (`migrate.py`) that performs the data changes
- A README documenting the purpose and approach
- Optional data files (CSV, Excel, JSON, JSONL) used by the migration
- Optional helper modules (e.g., scrapers, matchers) for complex migrations

## Migration Structure

Each migration folder follows this naming convention:
```
NNN-descriptive-name/
├── migrate.py          # Main migration script (required)
├── README.md           # Documentation (required)
├── source/             # Source data files (optional)
│   ├── data.jsonl      # JSONL format preferred for large datasets
│   └── data.csv        # CSV for tabular data
├── scraper.py          # Data scraper (optional)
└── helpers.py          # Helper modules (optional)
```

Where:
- `NNN` is a 3-digit numeric prefix (000-999) determining execution order
- `descriptive-name` is a kebab-case description of what the migration does

## Current Migrations

| Migration | Description | Status |
|-----------|-------------|--------|
| `000-example-migration` | Template and example migration structure | Example |
| `001-source-locations` | Import Nepal administrative locations (provinces, districts, municipalities, wards) | Applied |
| `002-ward-name-fix` | Fix ward naming inconsistencies | Applied |
| `003-source-2082-political-parties` | Import political parties from 2082 election data | Applied |
| `004-source-election-constituencies` | Import election constituencies | Applied |
| `005-seed-2079-election-candidates` | Import 2079 election candidates | Applied |
| `006-source-hospitals` | Import hospital data | Applied |
| `007-source-projects` | Import development projects from multiple sources (DFMIS, World Bank, ADB, JICA) | Applied |

## Migration Script Template

```python
"""
Migration: NNN-descriptive-name
Description: Brief description of what this migration does
Author: your-email@example.com
Date: YYYY-MM-DD
"""

# Migration metadata
AUTHOR = "your-email@example.com"
DATE = "YYYY-MM-DD"
DESCRIPTION = "Brief description of what this migration does"

async def migrate(context):
    """
    Main migration function.
    
    Args:
        context: MigrationContext with access to services and data
    """
    # Your migration logic here
    context.log("Migration started")
    
    # Example: Read data from JSONL
    # projects = []
    # with open(context.migration_dir / "source" / "data.jsonl") as f:
    #     for line in f:
    #         projects.append(json.loads(line))
    
    # Example: Create entities
    # for project in projects:
    #     entity = await context.publication.create_entity(...)
    
    context.log("Migration completed")
```

## Available Context Methods

The `context` object passed to your migration provides:

### Services
- `context.publication` - Publication Service for creating/updating entities
- `context.search` - Search Service for querying entities
- `context.db` - Direct database access (read-only)

> **Note on historical migrations:** Migrations
> `003-source-2082-political-parties`, `005-seed-2079-election-candidates`,
> `006-source-hospitals`, `007-source-projects`,
> `008-complete-political-parties`, and `010-source-2082-direct-candidates`
> import the now-removed scraping module (`nes.services.scraping` —
> `NameExtractor`, `GoogleVertexAIProvider`, `RateLimiter`/`RetryHandler`, and
> their `generate_translations.py` / scraper helpers). They have already been
> applied and are retained for historical reference only; re-running them
> requires a pre-removal version of NES. (`002-ward-name-fix` only mentions
> `context.scraping` in docstrings, so it has no such dependency.)

### File Helpers
- `context.read_csv(filename)` - Read CSV file from migration folder
- `context.read_json(filename)` - Read JSON file from migration folder
- `context.read_excel(filename, sheet_name)` - Read Excel file from migration folder

### Utilities
- `context.migration_dir` - Path to the migration folder
- `context.log(message)` - Log a message during migration execution

## Creating a Migration

1. **Copy the example migration**:
   ```bash
   cp -r migrations/000-example-migration migrations/NNN-your-migration-name
   ```

2. **Update the metadata** in `migrate.py`:
   - Set `AUTHOR` to your email
   - Set `DATE` to today's date (YYYY-MM-DD)
   - Set `DESCRIPTION` to describe what the migration does

3. **Implement the migration logic** in the `migrate()` function

4. **Document the migration** in `README.md`:
   - Purpose: What does this migration do?
   - Data Sources: Where does the data come from?
   - Changes: What entities/relationships are created/updated?
   - Dependencies: Does this depend on other migrations?
   - Notes: Any special considerations?

5. **Add data files** if needed (prefer JSONL for large datasets)

6. **Test locally**:
   ```bash
   nes migration run NNN-your-migration-name
   ```

7. **Submit a pull request** with your migration folder

## Running Migrations

```bash
# Run a specific migration
nes migration run 007-source-projects

# List all migrations
nes migration list
```

## Best Practices

1. **Keep migrations focused**: Each migration should do one thing well
2. **Use JSONL for large datasets**: One JSON object per line, easier to process
3. **Implement rollback**: Track created entities for cleanup on failure
4. **Document thoroughly**: Documentation is essential for this open-source project
5. **Include data sources**: Document where the data comes from
6. **Test before submitting**: Validate your migration locally
7. **Use descriptive names**: Make it clear what the migration does
8. **Preserve source data**: Keep original payloads when needed
9. **Implement deduplication**: For multi-source migrations, prevent duplicates

## Questions?

See the main documentation or ask in the project's discussion forum.
