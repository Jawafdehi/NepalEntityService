# API Consumer Guide

This guide is for developers who want to consume the Nepal Entity Service public API to build applications, conduct research, or explore Nepal's political landscape.

## Overview

The Nepal Entity Service provides a public, read-only RESTful API for accessing structured data about Nepali public entities including politicians, political parties, government organizations, and administrative locations.

**Public API Base URL**: `https://nes.jawafdehi.org/api`

## Key Concepts

### Entities

Entities are the core data objects in NES. There are three types:

- **Persons**: Politicians, public officials, and other public figures
- **Organizations**: Political parties, government bodies, NGOs
- **Locations**: Provinces, districts, municipalities, and wards

Each entity has:
- **Unique ID**: Hierarchical identifier (e.g., `entity:person/ram-chandra-poudel`)
- **Names**: Multilingual support (English and Nepali/Devanagari)
- **Attributes**: Type-specific metadata
- **Version History**: Complete audit trail of all changes

### Relationships

Relationships connect entities together:
- **MEMBER_OF**: Person → Organization (party membership)
- **AFFILIATED_WITH**: Person → Organization (affiliations)
- **EMPLOYED_BY**: Person → Organization (employment)
- **LOCATED_IN**: Entity → Location (geographic location)

Relationships can have temporal bounds (start/end dates) and their own version history.

### Versioning

Every change to entities and relationships is tracked:
- Complete snapshots of previous states
- Author attribution and timestamps
- Change descriptions for transparency
- Historical state retrieval

## Architecture

The API follows a layered architecture:

```
Client Application
       ↓
  FastAPI Service (https://nes.jawafdehi.org/api)
       ↓
  Search Service (Read-Optimized)
       ↓
  File-Based Database (Git-backed)
```

For detailed architecture, see the [Service Design](/specs/nepal-entity-service/design).

## API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/entities` | GET | Search and list entities |
| `/api/entities/{id}` | GET | Get specific entity |
| `/api/entities/{id}/relationships` | GET | Get entity relationships |
| `/api/entities/{id}/versions` | GET | Get version history |
| `/api/relationships` | GET | Query relationships |
| `/api/schemas` | GET | Discover entity types |
| `/api/health` | GET | Health check |

### Interactive Documentation

Visit the [OpenAPI documentation](https://nes.jawafdehi.org/docs) for:
- Complete endpoint reference
- Request/response schemas
- Interactive API testing
- Example requests

## Your First API Call

### Using cURL

```bash
curl "https://nes.jawafdehi.org/api/entities?query=poudel"
```

### Using Python

```python
import requests

response = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={"query": "poudel"}
)

data = response.json()
print(f"Found {data['total']} entities")

for entity in data['entities']:
    print(f"- {entity['names'][0]['en']['full']}")
```

### Using JavaScript

```javascript
fetch('https://nes.jawafdehi.org/api/entities?query=poudel')
  .then(response => response.json())
  .then(data => {
    console.log(`Found ${data.total} entities`);
    data.entities.forEach(entity => {
      console.log(`- ${entity.names[0].en.full}`);
    });
  });
```

## Common Operations

### Search for Entities

Search supports both English and Nepali:

```bash
# Search by English name
curl "https://nes.jawafdehi.org/api/entities?query=ram+chandra+poudel"

# Search by Nepali name
curl "https://nes.jawafdehi.org/api/entities?query=राम+चन्द्र+पौडेल"
```

### Filter by Entity Type

```bash
# Get all persons
curl "https://nes.jawafdehi.org/api/entities?entity_type=person"

# Get all political parties
curl "https://nes.jawafdehi.org/api/entities?entity_type=organization&sub_type=political_party"
```

### Filter by Tags

Tags allow you to categorize and filter entities by specific groups or categories:

```bash
# Get all 2079 Federal election elected representatives
curl "https://nes.jawafdehi.org/api/entities?tags=federal-election-2079-elected"

# Get all 2079 Federal election candidates (both elected and non-elected)
curl "https://nes.jawafdehi.org/api/entities?tags=federal-election-2079-candidate"

# Combine tags with entity type (get only person entities who were elected in 2079 Federal election)
curl "https://nes.jawafdehi.org/api/entities?entity_type=person&tags=federal-election-2079-elected"
```

**Tag Filtering Rules:**
- **Multiple tags use AND logic**: Entity must have ALL specified tags
- **Tags can be combined with other filters**: type, subtype, query, etc.
- **Comma-separated**: `tags=tag1,tag2,tag3`

**Example: Find all candidates in both federal and provincial elections in 2079**

```bash
# Get entities with BOTH tags (candidates who ran for both federal and provincial seats)
curl "https://nes.jawafdehi.org/api/entities?tags=federal-election-2079-candidate,provincial-election-2079-candidate"
```

**Python Example:**

```python
import requests

# Get all 2079 Federal election elected representatives
response = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={
        "entity_type": "person",
        "tags": "federal-election-2079-elected"
    }
)

elected = response.json()
print(f"Found {elected['total']} elected representatives")

for person in elected['entities']:
    name = person['names'][0]['en']['full']
    tags = ', '.join(person.get('tags', []))
    constituency = person['attributes'].get('constituency', 'Unknown')
    print(f"- {name} ({constituency})")
    print(f"  Tags: {tags}")
```

**JavaScript Example:**

```javascript
// Fetch all 2082 Federal election candidates
fetch('https://nes.jawafdehi.org/api/entities?tags=federal-election-2082-candidate')
  .then(response => response.json())
  .then(data => {
    console.log(`Found ${data.total} candidates for 2082 Federal election`);
    data.entities.forEach(entity => {
      const name = entity.names[0].en.full;
      const tags = entity.tags || [];
      console.log(`- ${name}`);
      console.log(`  Tags: ${tags.join(', ')}`);
    });
  });
```

**Available Tags in the System:**

| Tag | Description |
|-----|-------------|
| `federal-election-2079-elected` | Elected in 2079 Federal election |
| `provincial-election-2079-elected` | Elected in 2079 Provincial election |
| `federal-election-2079-candidate` | Candidate in 2079 Federal election |
| `provincial-election-2079-candidate` | Candidate in 2079 Provincial election |
| `federal-election-2082-candidate` | Candidate in 2082 Federal election |

### Get a Specific Entity

```bash
curl "https://nes.jawafdehi.org/api/entities/entity:person/ram-chandra-poudel"
```

### Query Relationships

```bash
# Get all relationships for an entity
curl "https://nes.jawafdehi.org/api/entities/entity:person/ram-chandra-poudel/relationships"

# Filter by relationship type
curl "https://nes.jawafdehi.org/api/entities/entity:person/ram-chandra-poudel/relationships?relationship_type=MEMBER_OF"
```

### Get Version History

```bash
curl "https://nes.jawafdehi.org/api/entities/entity:person/ram-chandra-poudel/versions"
```

## Pagination

All list endpoints support pagination:

```bash
# Get first 10 results
curl "https://nes.jawafdehi.org/api/entities?limit=10&offset=0"

# Get next 10 results
curl "https://nes.jawafdehi.org/api/entities?limit=10&offset=10"
```

## Response Format

All API responses follow a consistent JSON format:

```json
{
  "entities": [...],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

Error responses include detailed error information:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Entity not found"
  }
}
```

## Rate Limiting

The public API has rate limits to ensure fair usage:

- **100 requests per minute** per IP address
- **1000 requests per hour** per IP address

If you need higher limits, please contact us about dedicated access.

## CORS Support

The API supports CORS (Cross-Origin Resource Sharing), allowing you to make requests from web applications:

```javascript
// Works from any origin
fetch('https://nes.jawafdehi.org/api/entities')
  .then(response => response.json())
  .then(data => console.log(data));
```

## Data Models

For detailed information about entity and relationship schemas, see the [Data Models](/consumers/data-models) documentation.

## Use Cases

The Nepal Entity Service API is designed for:

- **Civic Technology Applications**: Build transparency and accountability platforms
- **Research and Analysis**: Analyze political and organizational networks
- **Data Journalism**: Track relationships and changes over time
- **Government Transparency**: Provide public access to entity information
- **Academic Research**: Study Nepal's political and administrative structures

## Next Steps

- Explore the [Interactive OpenAPI Documentation](https://nes.jawafdehi.org/docs)
- Review [Data Models](/consumers/data-models) to understand entity schemas
- Check out [Examples](/consumers/examples) for common usage patterns
- Learn about the [Service Design](/specs/nepal-entity-service/design)

## Need Help?

- Check the [Examples](/consumers/examples) page for common patterns
- Review the [OpenAPI documentation](https://nes.jawafdehi.org/docs) for detailed endpoint reference
- Visit our [GitHub repository](https://github.com/Jawafdehi/NepalEntityService) for issues and discussions
