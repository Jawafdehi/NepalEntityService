# Getting Started

This guide will help you get started with the Nepal Entity Service API. Whether you're building a web application, conducting research, or exploring Nepal's political landscape, this guide covers everything you need to know.

## Installation

### Using the Public API

The easiest way to use Nepal Entity Service is through the public API. No installation required - just make HTTP requests to the API endpoints.

**Base URL**: `https://nes.jawafdehi.org/api`

> **Note:** If you're running your own instance locally, replace `https://nes.jawafdehi.org/api` with `http://localhost:8195/api` in all examples below.

### Installing the Python Package

If you want to run your own instance or use the data maintainer interface:

> Note: Still in the process of deploying to PyPI.

```bash
# Install with pip
pip install nepal-entity-service

# Or with poetry
poetry add nepal-entity-service
```

### Running Your Own Instance

To run your own instance of the API:

```bash
# Clone the repository
git clone https://github.com/Jawafdehi/NepalEntityService.git
cd NepalEntityService

# Clone the database repository and set NES_DB_URL
git clone --depth 1 https://github.com/Jawafdehi/NepalEntityService-database.git ./nes-db
export NES_DB_URL=file://$(pwd)/nes-db/v2

# Install dependencies with poetry
poetry install

# Start the API server
poetry run nes server start
```

The API will be available at `http://localhost:8195`.

## Your First API Call

Let's make your first API call to search for entities:

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

Search for entities by name (supports both English and Nepali):

```bash
# Search by English name
curl "https://nes.jawafdehi.org/api/entities?query=ram+chandra+poudel"

# Search by Nepali name
curl "https://nes.jawafdehi.org/api/entities?query=राम+चन्द्र+पौडेल"
```

### Filter by Entity Type

Filter entities by type (person, organization, location):

```bash
# Get all persons
curl "https://nes.jawafdehi.org/api/entities?entity_type=person"

# Get all political parties
curl "https://nes.jawafdehi.org/api/entities?entity_type=organization&sub_type=political_party"
```

### Get a Specific Entity

Retrieve a specific entity by its ID:

```bash
curl "https://nes.jawafdehi.org/api/entities/entity:person/ram-chandra-poudel"
```

### Query Relationships

Find relationships for an entity:

```bash
# Get all relationships for an entity
curl "https://nes.jawafdehi.org/api/entities/entity:person/ram-chandra-poudel/relationships"

# Filter by relationship type
curl "https://nes.jawafdehi.org/api/entities/entity:person/ram-chandra-poudel/relationships?relationship_type=MEMBER_OF"
```

### Get Version History

Retrieve the version history for an entity:

```bash
curl "https://nes.jawafdehi.org/api/entities/entity:person/ram-chandra-poudel/versions"
```

## Pagination

All list endpoints support pagination using `limit` and `offset` parameters:

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

## Next Steps

Now that you've made your first API calls, explore:

- [API Reference](/docs) - Interactive OpenAPI documentation
- [Data Models](/consumers/data-models) - Understanding entity and relationship schemas
- [Examples](/consumers/examples) - More complex usage examples
- [Service Design](/specs/nepal-entity-service/design) - Learn about the system design

## Need Help?

- Check the [Examples](/consumers/examples) page for common patterns
- Review the [API Reference](/docs) for detailed documentation
- Visit the [OpenAPI documentation](/docs) for interactive API exploration
