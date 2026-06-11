# Nepal Entity Service - Examples

This directory contains example scripts demonstrating how to use the Nepal Entity Service (nes) for data maintenance operations. All examples use authentic Nepali political data.

## Prerequisites

1. Install the nes package:
   ```bash
   poetry install
   ```

2. Ensure you have a database at `nes-db/v2` with some initial data, or the examples will create entities as needed.

## Examples

### 1. Update Entity (`update_entity.py`)

Demonstrates how to update an existing entity with automatic versioning.

**What it shows:**
- Retrieving an existing entity
- Modifying entity attributes
- Updating with automatic version creation
- Viewing version history

**Run:**
```bash
python examples/update_entity.py
```

**Example entity:** Ram Chandra Poudel (President of Nepal)

---

### 2. Create Relationship (`create_relationship.py`)

Demonstrates how to create relationships between entities.

**What it shows:**
- Creating MEMBER_OF relationships between politicians and parties
- Adding temporal information (start/end dates)
- Querying relationships for an entity
- Viewing relationship version history

**Run:**
```bash
python examples/create_relationship.py
```

**Example relationships:** Political party memberships for Nepali politicians

---

### 3. Batch Import (`batch_import.py`)

Demonstrates how to import multiple entities in a batch operation.

**What it shows:**
- Importing multiple entities at once
- Handling errors gracefully during import
- Tracking import statistics
- Verifying imported data

**Run:**
```bash
python examples/batch_import.py
```

**Example data:** Nepali political parties (Nepali Congress, CPN-UML, CPN-MC, RSP, NSP)

---

### 4. Version History (`version_history.py`)

Demonstrates how to explore version history and audit trails.

**What it shows:**
- Viewing complete version history
- Comparing versions to see changes
- Retrieving specific historical versions
- Tracking who made changes and when
- Analyzing change patterns

**Run:**
```bash
python examples/version_history.py
```

**Example entity:** Pushpa Kamal Dahal (Prachanda)

---

## Common Patterns

### Initialize Services

All examples follow this pattern:

```python
from pathlib import Path
from nes.database.file_database import FileDatabase
from nes.services.publication import PublicationService

# Initialize database
db_path = Path("nes-db/v2")
db = FileDatabase(base_path=str(db_path))

# Initialize publication service
pub_service = PublicationService(database=db)
```

### Create an Entity

```python
entity_data = {
    "slug": "ram-chandra-poudel",
    "type": "person",
    "sub_type": "politician",
    "names": [
        {
            "kind": "PRIMARY",
            "en": {"full": "Ram Chandra Poudel"},
            "ne": {"full": "राम चन्द्र पौडेल"}
        }
    ],
    "attributes": {
        "party": "nepali-congress",
        "position": "President"
    }
}

entity = await pub_service.create_entity(
    entity_data=entity_data,
    author_id="author:human:data-maintainer",
    change_description="Initial import"
)
```

### Update an Entity

```python
# Get existing entity
entity = await pub_service.get_entity("entity:person/ram-chandra-poudel")

# Modify attributes
entity.attributes["position"] = "President of Nepal"

# Update with versioning
updated = await pub_service.update_entity(
    entity=entity,
    author_id="author:human:data-maintainer",
    change_description="Updated position"
)
```

### Create a Relationship

```python
relationship = await pub_service.create_relationship(
    source_entity_id="entity:person/ram-chandra-poudel",
    target_entity_id="entity:organization/political_party/nepali-congress",
    relationship_type="MEMBER_OF",
    start_date=date(1970, 1, 1),
    attributes={"role": "Senior Leader"},
    author_id="author:human:data-maintainer",
    change_description="Added party membership"
)
```

### Query Relationships

```python
from nes.services.search import SearchService

search_service = SearchService(database=db)

# Find all relationships for an entity
relationships = await search_service.search_relationships(
    source_entity_id="entity:person/ram-chandra-poudel",
    limit=10
)

# Find all MEMBER_OF relationships
memberships = await search_service.search_relationships(
    relationship_type="MEMBER_OF",
    limit=20
)
```

### View Version History

```python
# Get all versions for an entity
versions = await pub_service.get_entity_versions(
    "entity:person/ram-chandra-poudel"
)

for version in versions:
    print(f"Version {version.version_number}")
    print(f"  Created: {version.created_at}")
    print(f"  Author: {version.author.slug}")
    print(f"  Description: {version.change_description}")
```

## Authentic Nepali Data

All examples use authentic Nepali data including:

- **Politicians:** Pushpa Kamal Dahal (Prachanda), Sher Bahadur Deuba, KP Sharma Oli, Ram Chandra Poudel, etc.
- **Political Parties:** Nepali Congress, CPN-UML, CPN Maoist Centre, Rastriya Swatantra Party, etc.
- **Locations:** Provinces, districts, municipalities from Nepal's administrative structure
- **Government Bodies:** Ministries, constitutional offices, etc.

All names include both English and Nepali (Devanagari) variants.

## Error Handling

All examples include proper error handling:

```python
try:
    entity = await pub_service.create_entity(
        entity_data=entity_data,
        author_id="author:human:data-maintainer",
        change_description="Import"
    )
except ValueError as e:
    print(f"Validation error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Next Steps

After running these examples, you can:

1. Explore the Jupyter notebook examples in `notebooks/`
2. Read the Data Maintainer Guide in `docs/data-maintainer-guide.md`
3. Build your own data maintenance scripts
4. Use the CLI tools for interactive data management

## Support

For questions or issues:
- Check the documentation in `docs/`
- Review the test files in `tests/` for more examples
- Refer to the API documentation at `/docs` when running the server
