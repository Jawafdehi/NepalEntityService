# Batch Entity Lookup Endpoint Design

**Status**: Draft  
**Created**: 2024-12-04  
**Author**: System  
**Related**: api-guide.md, design-patterns.md

## Overview

This document outlines the design for a batch entity lookup endpoint in the Nepal Entity Service API. The endpoint will allow clients to fetch multiple entities in a single HTTP request, eliminating the N+1 query problem when displaying lists of entities.

## Problem Statement

### Current State

The NES API currently supports fetching entities one at a time:

```bash
GET /api/entities/entity:person/ram-chandra-poudel
GET /api/entities/entity:person/kp-sharma-oli
GET /api/entities/entity:person/pushpa-kamal-dahal
# ... N requests for N entities
```

### Issues

1. **N+1 Query Problem**: Clients like Jawafdehi need to make N API calls to fetch N entities
2. **Performance**: Each HTTP request has overhead (DNS, TCP handshake, TLS, latency)
3. **Network Efficiency**: Multiple round trips increase total page load time
4. **Rate Limiting**: N requests consume rate limit quota faster

### Use Case

Jawafdehi API stores entity references as `nes_id` fields in `JawafEntity` model. When displaying entity lists, the frontend needs to:

1. Fetch JawafEntity records from JDS API (returns list of `nes_id` values)
2. Enrich with NES data for display (names, pictures, attributes)
3. Currently makes N separate API calls to NES

**Example**: Displaying 20 entities requires 20 separate HTTP requests to NES API.

## Proposed Solution

### Batch Lookup Endpoint

Add support for fetching multiple entities in a single request using comma-separated entity IDs:

```bash
GET /api/entities?ids=entity%3Aperson%2Fram-chandra-poudel%2Centity%3Aperson%2Fkp-sharma-oli%2Centity%3Aperson%2Fpushpa-kamal-dahal
```

**Note**: Entity IDs contain special characters (`:` and `/`) that must be URL-encoded in query parameters.

### Design Principles

1. **Backward Compatibility**: Existing `/api/entities` search endpoint continues to work
2. **RESTful**: Use query parameters for filtering, not POST body
3. **Efficient**: Single database query to fetch all requested entities
4. **Robust**: Handle missing entities gracefully (partial success)
5. **Limited**: Enforce maximum batch size to prevent abuse

## API Design

### Endpoint

```
GET /api/entities
```

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ids` | string | No | Comma-separated entity IDs (max 25) |
| `query` | string | No | Text search (existing parameter) |
| `entity_type` | string | No | Filter by type (existing parameter) |
| `limit` | integer | No | Max results (existing parameter) |
| `offset` | integer | No | Pagination offset (existing parameter) |

**Note**: `ids` parameter is mutually exclusive with all other parameters (`query`, `entity_type`, `sub_type`, `attributes`, `limit`, `offset`).

### Request Examples

#### Comma-Separated Syntax

```bash
GET /api/entities?ids=entity%3Aperson%2Fram-chandra-poudel%2Centity%3Aperson%2Fkp-sharma-oli
```

**Rationale**: Compact URL, easy to construct programmatically, single parameter to parse.

**URL Encoding Note**: Entity IDs must be URL-encoded:
- `:` becomes `%3A`
- `/` becomes `%2F`
- `,` becomes `%2C` (separator between entity IDs)

### Response Format

#### Success Response (200 OK)

```json
{
  "entities": [
    {
      "id": "entity:person/ram-chandra-poudel",
      "entity_type": "person",
      "names": [...],
      "attributes": {...},
      "version": {...}
    },
    {
      "id": "entity:person/kp-sharma-oli",
      "entity_type": "person",
      "names": [...],
      "attributes": {...},
      "version": {...}
    }
  ],
  "total": 2,
  "requested": 3,
  "not_found": [
    "entity:person/non-existent-entity"
  ]
}
```

**Response Fields**:
- `entities`: Array of entity objects (only found entities)
- `total`: Count of entities returned
- `requested`: Count of entity IDs requested
- `not_found`: Array of entity IDs that were not found (optional, only if some missing)

#### Partial Success

If some entities are not found, the endpoint returns 200 OK with found entities and lists missing IDs in `not_found` field.

**Rationale**: Partial success is acceptable. Client can handle missing entities gracefully.

#### Error Responses

**400 Bad Request** - Invalid parameters:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The 'ids' parameter cannot be combined with other parameters"
  }
}
```

**400 Bad Request** - Batch size exceeded:

```json
{
  "error": {
    "code": "BATCH_SIZE_EXCEEDED",
    "message": "Maximum batch size is 25. Requested: 30"
  }
}
```

**500 Internal Server Error** - Server error:

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An internal error occurred"
  }
}
```

## Implementation Design

### Architecture

```
Client Request
     ↓
FastAPI Router (entities.py)
     ↓
SearchService.get_entities_batch(entity_ids: List[str])
     ↓
Database.get_entities_batch(entity_ids: List[str])
     ↓
File System (parallel reads)
```

### Code Structure

#### 1. Update Router (`nes/api/routes/entities.py`)

Modify `list_entities` endpoint to detect batch lookup parameters:

```python
@router.get("", response_model=EntityListResponse)
async def list_entities(
    ids: Optional[str] = Query(None, description="Comma-separated entity IDs for batch lookup (max 25)"),
    query: Optional[str] = Query(None, description="Text query to search"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    sub_type: Optional[str] = Query(None, description="Filter by entity subtype"),
    attributes: Optional[str] = Query(None, description="Filter by attributes"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    search_service: SearchService = Depends(get_search_service),
):
    """List or search entities with optional filtering and pagination.
    
    Supports two modes:
    1. Batch lookup: Provide 'ids' parameter to fetch specific entities (max 25)
    2. Search/filter: Provide 'query', 'entity_type', etc. to search entities
    
    The 'ids' parameter cannot be combined with any other parameters.
    """
    # Validate mutually exclusive parameters
    other_params = [query, entity_type, sub_type, attributes, limit != 100, offset != 0]
    
    if ids and any(other_params):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "The 'ids' parameter cannot be combined with other parameters"
                }
            }
        )
    
    # Batch lookup mode
    if ids:
        return await _batch_lookup_entities(
            ids=ids, search_service=search_service
        )
    
    # Search/filter mode (existing implementation)
    return await _search_entities(
        query=query,
        entity_type=entity_type,
        sub_type=sub_type,
        attributes=attributes,
        limit=limit,
        offset=offset,
        search_service=search_service,
    )
```

#### 2. Batch Lookup Handler

```python
async def _batch_lookup_entities(
    ids: str,
    search_service: SearchService,
) -> EntityListResponse:
    """Handle batch entity lookup by IDs."""
    # Parse comma-separated entity IDs
    entity_ids = [eid.strip() for eid in ids.split(",") if eid.strip()]
    
    # Validate batch size
    MAX_BATCH_SIZE = 25
    if len(entity_ids) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "BATCH_SIZE_EXCEEDED",
                    "message": f"Maximum batch size is {MAX_BATCH_SIZE}. Requested: {len(entity_ids)}"
                }
            }
        )
    
    # Validate entity IDs are not empty
    if not entity_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "At least one entity ID is required"
                }
            }
        )
    
    try:
        # Fetch entities in batch
        result = await search_service.get_entities_batch(entity_ids)
        
        # Build response
        entity_dicts = [entity.model_dump(mode="json") for entity in result.entities]
        
        response_data = {
            "entities": entity_dicts,
            "total": len(entity_dicts),
            "requested": len(entity_ids),
        }
        
        # Include not_found field if any entities were missing
        if result.not_found:
            response_data["not_found"] = result.not_found
        
        return EntityListResponse(**response_data)
    
    except Exception as e:
        logger.error(f"Error in batch entity lookup: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "BATCH_LOOKUP_ERROR",
                    "message": "An error occurred during batch entity lookup"
                }
            }
        )
```

#### 3. Search Service Method (`nes/services/search.py`)

```python
from dataclasses import dataclass
from typing import List

@dataclass
class BatchLookupResult:
    """Result of batch entity lookup."""
    entities: List[Entity]
    not_found: List[str]

class SearchService:
    """Service for searching and retrieving entities."""
    
    async def get_entities_batch(self, entity_ids: List[str]) -> BatchLookupResult:
        """
        Fetch multiple entities by their IDs in a single operation.
        
        Args:
            entity_ids: List of entity IDs to fetch
            
        Returns:
            BatchLookupResult with found entities and list of not found IDs
        """
        entities = []
        not_found = []
        
        # Fetch entities concurrently
        tasks = [self.database.get_entity(entity_id) for entity_id in entity_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for entity_id, result in zip(entity_ids, results):
            if isinstance(result, Exception):
                logger.warning(f"Error fetching entity {entity_id}: {result}")
                not_found.append(entity_id)
            elif result is None:
                not_found.append(entity_id)
            else:
                entities.append(result)
        
        return BatchLookupResult(entities=entities, not_found=not_found)
```

#### 4. Database Layer (Optional Optimization)

For file-based database, the current implementation using `asyncio.gather` is sufficient. For future database backends (PostgreSQL, etc.), add optimized batch query:

```python
class Database(ABC):
    """Abstract database interface."""
    
    @abstractmethod
    async def get_entities_batch(self, entity_ids: List[str]) -> List[Optional[Entity]]:
        """
        Fetch multiple entities in a single database query.
        
        Returns list in same order as entity_ids, with None for missing entities.
        """
        pass
```

### Response Model Update

Update `EntityListResponse` to include optional fields:

```python
class EntityListResponse(BaseModel):
    """Response model for entity list endpoints."""
    entities: List[Dict[str, Any]]
    total: int
    requested: Optional[int] = None  # Only for batch lookup
    not_found: Optional[List[str]] = None  # Only for batch lookup
    limit: Optional[int] = None  # Only for search/filter
    offset: Optional[int] = None  # Only for search/filter
```

## Configuration

### Batch Size Limit

```python
# nes/config.py
class Config:
    MAX_BATCH_SIZE = 25  # Maximum entities per batch request
```

**Rationale**: 
- Prevents abuse and resource exhaustion
- 25 entities is sufficient for typical UI pagination (showing 20-25 items per page)
- Keeps response size manageable
- Encourages proper pagination in client applications

### Rate Limiting

Batch requests count as 1 request for rate limiting purposes, not N requests.

**Rationale**: Encourages clients to use batch endpoint instead of individual requests.

## Testing Strategy

### Unit Tests

```python
# tests/services/test_search_service.py

@pytest.mark.asyncio
async def test_get_entities_batch_all_found(search_service, sample_entities):
    """Test batch lookup when all entities exist."""
    entity_ids = [e.id for e in sample_entities[:3]]
    
    result = await search_service.get_entities_batch(entity_ids)
    
    assert len(result.entities) == 3
    assert len(result.not_found) == 0
    assert all(e.id in entity_ids for e in result.entities)


@pytest.mark.asyncio
async def test_get_entities_batch_partial_found(search_service, sample_entities):
    """Test batch lookup when some entities don't exist."""
    entity_ids = [
        sample_entities[0].id,
        "entity:person/non-existent",
        sample_entities[1].id,
    ]
    
    result = await search_service.get_entities_batch(entity_ids)
    
    assert len(result.entities) == 2
    assert len(result.not_found) == 1
    assert "entity:person/non-existent" in result.not_found


@pytest.mark.asyncio
async def test_get_entities_batch_none_found(search_service):
    """Test batch lookup when no entities exist."""
    entity_ids = ["entity:person/fake1", "entity:person/fake2"]
    
    result = await search_service.get_entities_batch(entity_ids)
    
    assert len(result.entities) == 0
    assert len(result.not_found) == 2


@pytest.mark.asyncio
async def test_get_entities_batch_empty_list(search_service):
    """Test batch lookup with empty list."""
    result = await search_service.get_entities_batch([])
    
    assert len(result.entities) == 0
    assert len(result.not_found) == 0
```

### API Integration Tests

```python
# tests/api/test_entities_batch.py

@pytest.mark.asyncio
async def test_batch_lookup_comma_separated(client, sample_entities):
    """Test batch lookup using comma-separated 'ids' parameter."""
    entity_ids = [sample_entities[0].id, sample_entities[1].id]
    ids_param = ",".join(entity_ids)
    
    response = await client.get(f"/api/entities?ids={ids_param}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["requested"] == 2
    assert "not_found" not in data


@pytest.mark.asyncio
async def test_batch_lookup_with_not_found(client, sample_entities):
    """Test batch lookup with some missing entities."""
    entity_ids = [sample_entities[0].id, "entity:person/missing"]
    ids_param = ",".join(entity_ids)
    
    response = await client.get(f"/api/entities?ids={ids_param}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["requested"] == 2
    assert len(data["not_found"]) == 1
    assert "entity:person/missing" in data["not_found"]


@pytest.mark.asyncio
async def test_batch_lookup_exceeds_limit(client):
    """Test batch lookup with too many entity IDs."""
    entity_ids = [f"entity:person/fake{i}" for i in range(26)]
    ids_param = ",".join(entity_ids)
    
    response = await client.get(f"/api/entities?ids={ids_param}")
    
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "BATCH_SIZE_EXCEEDED"


@pytest.mark.asyncio
async def test_batch_lookup_with_query_param_fails(client):
    """Test that batch lookup cannot be combined with query parameter."""
    response = await client.get(
        "/api/entities?ids=entity:person/test&query=poudel"
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_batch_lookup_with_entity_type_fails(client):
    """Test that batch lookup cannot be combined with entity_type parameter."""
    response = await client.get(
        "/api/entities?ids=entity:person/test&entity_type=person"
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_batch_lookup_with_limit_fails(client):
    """Test that batch lookup cannot be combined with limit parameter."""
    response = await client.get(
        "/api/entities?ids=entity:person/test&limit=50"
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_batch_lookup_with_offset_fails(client):
    """Test that batch lookup cannot be combined with offset parameter."""
    response = await client.get(
        "/api/entities?ids=entity:person/test&offset=10"
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_batch_lookup_empty_ids(client):
    """Test batch lookup with empty ids parameter."""
    response = await client.get("/api/entities?ids=")
    
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_batch_lookup_with_whitespace(client, sample_entities):
    """Test batch lookup handles whitespace in comma-separated list."""
    entity_ids = [sample_entities[0].id, sample_entities[1].id]
    ids_param = f"{entity_ids[0]} , {entity_ids[1]} "
    
    response = await client.get(f"/api/entities?ids={ids_param}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
```

### Property-Based Tests

```python
# tests/api/test_entities_batch_properties.py

from hypothesis import given, strategies as st

@given(
    entity_count=st.integers(min_value=1, max_value=25),
    missing_count=st.integers(min_value=0, max_value=5)
)
@pytest.mark.asyncio
async def test_batch_lookup_properties(client, sample_entities, entity_count, missing_count):
    """Property: batch lookup returns correct counts and preserves entity data."""
    # Select existing entities
    existing_ids = [sample_entities[i % len(sample_entities)].id for i in range(entity_count)]
    
    # Add some non-existent IDs
    missing_ids = [f"entity:person/missing{i}" for i in range(missing_count)]
    
    all_ids = existing_ids + missing_ids
    
    response = await client.get(
        "/api/entities",
        params=[("id", eid) for eid in all_ids]
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Property: requested count matches input
    assert data["requested"] == len(all_ids)
    
    # Property: total + not_found = requested
    assert data["total"] + len(data.get("not_found", [])) == data["requested"]
    
    # Property: all returned entities have valid IDs
    returned_ids = [e["id"] for e in data["entities"]]
    assert all(eid in all_ids for eid in returned_ids)
    
    # Property: not_found contains only missing IDs
    if "not_found" in data:
        assert all(eid in missing_ids for eid in data["not_found"])
```

## Performance Considerations

### Expected Performance

**Current (N requests)**:
- 20 entities × 100ms per request = 2000ms total
- Network overhead: 20 × (DNS + TCP + TLS) ≈ 20 × 50ms = 1000ms
- **Total: ~3000ms**

**With Batch (1 request)**:
- 1 request × 100ms = 100ms
- Network overhead: 1 × 50ms = 50ms
- **Total: ~150ms**

**Improvement: 20× faster**

### Scalability

- File-based database: Parallel file reads using `asyncio.gather`
- Future SQL database: Single `WHERE id IN (...)` query
- In-memory cache: O(1) lookup per entity

### Caching

Batch requests benefit from in-memory cache:
- First request: Cache miss, load from disk
- Subsequent requests: Cache hit, instant response
- Cache warming on startup loads frequently accessed entities

## Migration Plan

### Phase 1: Implementation (TDD)

1. Write failing tests for batch lookup functionality
2. Implement `SearchService.get_entities_batch()` method
3. Implement `_batch_lookup_entities()` handler
4. Update `list_entities()` router to support batch parameters
5. Update response models
6. Run tests until all pass

### Phase 2: Documentation

1. Update API guide with batch lookup examples
2. Update OpenAPI schema (automatic via FastAPI)
3. Add usage examples for consumers
4. Document performance improvements

### Phase 3: Client Updates

1. Update Jawafdehi frontend to use batch endpoint
2. Measure performance improvement
3. Update other clients (if any)

### Phase 4: Monitoring

1. Track batch endpoint usage metrics
2. Monitor batch size distribution
3. Adjust `MAX_BATCH_SIZE` if needed
4. Monitor error rates

## Client Usage Example

### Before (N+1 Queries)

```bash
# N separate requests
curl "https://nes.jawafdehi.org/api/entities/entity%3Aperson%2Fram-chandra-poudel"
curl "https://nes.jawafdehi.org/api/entities/entity%3Aperson%2Fkp-sharma-oli"
curl "https://nes.jawafdehi.org/api/entities/entity%3Aperson%2Fpushpa-kamal-dahal"
# ... 20 requests total
```

### After (Batch Query)

```bash
# Single batch request (up to 25 entities)
curl "https://nes.jawafdehi.org/api/entities?ids=entity%3Aperson%2Fram-chandra-poudel%2Centity%3Aperson%2Fkp-sharma-oli%2Centity%3Aperson%2Fpushpa-kamal-dahal"
```

**Note**: Clients fetching more than 25 entities should split requests into multiple batches of 25 and fetch them in parallel.

## Security Considerations

### Input Validation

- Validate entity ID format (must match `entity:type/slug` pattern)
- Sanitize entity IDs to prevent injection attacks
- Enforce maximum batch size to prevent resource exhaustion

### Rate Limiting

- Batch requests count as 1 request (not N)
- Apply same rate limits as individual entity requests
- Monitor for abuse patterns (e.g., always requesting max batch size)

### Authorization

- Batch endpoint is read-only (GET)
- No authentication required (public API)
- Same access control as individual entity endpoint

## Open Questions

1. **Ordering**: Should response preserve request order?
   - **Recommendation**: No ordering guarantee. Clients should map by ID.

2. **Partial Failure**: Should we return 200 OK or 207 Multi-Status for partial success?
   - **Recommendation**: 200 OK with `not_found` field. Simpler for clients.

3. **Batch Size**: Is 25 entities sufficient?
   - **Decision**: Yes, 25 matches typical pagination sizes and keeps responses manageable.

4. **Pagination**: Should batch lookup support pagination?
   - **Recommendation**: No. Batch lookup is for specific IDs, not browsing.

## Success Metrics

- **Performance**: Page load time reduced by 80%+ for entity lists
- **API Calls**: N requests reduced to 1 request
- **Adoption**: Jawafdehi switches to batch endpoint within 1 week
- **Errors**: < 1% error rate on batch endpoint
- **Usage**: Batch endpoint becomes primary method for entity retrieval

## References

- [API Consumer Guide](../consumers/api-guide.md)
- [Design Patterns](./design-patterns.md)
- [Search Service Guide](./search-service-guide.md)
- [Jawafdehi Entity Search Redesign](../../../JawafdehiAPI/docs/entity-search-redesign.md)
