# Design Patterns

This document outlines the opinionated design patterns and conventions used in the Nepal Entity Service project. Following these patterns ensures consistency, maintainability, and readability across the codebase.

## Import Style

### Prefer Absolute Imports

Use absolute imports over relative imports in Python code for better clarity and maintainability.

**Good:**
```python
from nes.models.entity import Entity
from nes.services.entity_service import EntityService
```

**Avoid:**
```python
from ..models.entity import Entity
from .entity_service import EntityService
```

### Module-Level Imports

Place imports at the module level rather than inside functions. This improves readability and performance by avoiding repeated import overhead.

**Good:**
```python
from nes.database.connection import get_session
from nes.models.entity import Entity

def create_entity(name: str):
    session = get_session()
    entity = Entity(name=name)
    # ...
```

**Avoid:**
```python
def create_entity(name: str):
    from nes.database.connection import get_session
    from nes.models.entity import Entity
    
    session = get_session()
    entity = Entity(name=name)
    # ...
```

**Exception:** Local imports are acceptable in the following cases:
- Avoiding circular dependencies
- Optional dependencies that may not be installed
- Heavy imports that are rarely used in a module

**Example of acceptable local import:**
```python
def run_api_server():
    # Only import if the API functionality is actually used
    try:
        import uvicorn

        from nes.api.app import app
    except ImportError:
        raise RuntimeError("API dependencies not installed. Install with: pip install nepal-entity-service[api]")

    uvicorn.run(app)
```

## Code Organization

### Module Structure

Organize code into logical modules following this hierarchy:
- `models/`: Data models and schemas
- `services/`: Business logic and service layer
- `api/`: API endpoints and routing
- `database/`: Database connections and utilities
- `cli/`: Command-line interface commands
- `core/`: Core utilities and shared functionality

### Naming Conventions

- **Files**: Use snake_case for Python files (e.g., `entity_service.py`)
- **Classes**: Use PascalCase (e.g., `EntityService`, `RelationshipManager`)
- **Functions/Methods**: Use snake_case (e.g., `get_entity`, `create_relationship`)
- **Constants**: Use UPPER_SNAKE_CASE (e.g., `DEFAULT_PAGE_SIZE`, `MAX_RETRIES`)

## Error Handling

### Explicit Error Messages

Provide clear, actionable error messages that help users understand what went wrong and how to fix it.

**Good:**
```python
if not entity_id:
    raise ValueError("Entity ID is required. Provide a valid entity identifier.")
```

**Avoid:**
```python
if not entity_id:
    raise ValueError("Invalid input")
```

### Use Appropriate Exception Types

Choose exception types that accurately represent the error condition:
- `ValueError`: Invalid argument values
- `TypeError`: Wrong argument types
- `FileNotFoundError`: Missing files or resources
- `RuntimeError`: Runtime conditions that don't fit other categories

## Documentation

### Docstrings

Use clear, concise docstrings for all public functions, classes, and modules:

```python
def get_entity_by_id(entity_id: str) -> Entity:
    """
    Retrieve an entity by its unique identifier.
    
    Args:
        entity_id: The unique identifier of the entity
        
    Returns:
        The entity object if found
        
    Raises:
        EntityNotFoundError: If no entity exists with the given ID
    """
    # Implementation
```

### Type Hints

Use type hints consistently throughout the codebase to improve code clarity and enable better IDE support:

```python
from typing import List, Optional

def search_entities(query: str, limit: Optional[int] = None) -> List[Entity]:
    # Implementation
```

## Testing

### Test Organization

Mirror the source code structure in tests:
- `tests/models/`: Tests for models
- `tests/services/`: Tests for services
- `tests/api/`: Tests for API endpoints

### Test Naming

Use descriptive test names that explain what is being tested:

```python
def test_create_entity_with_valid_data():
    # Test implementation

def test_create_entity_raises_error_when_name_is_empty():
    # Test implementation
```

## Configuration

### Environment Variables

Use environment variables for configuration that may change between environments:
- Database paths
- API keys
- Feature flags
- Port numbers

### Configuration Files

Keep configuration centralized in `nes/config.py` for easy maintenance and discoverability.

## Additional Resources

For more specific guidance, see:
- [Contributor Guide](contributor-guide.md)
- [Database Setup](database-setup.md)
- [Migration Architecture](migration-architecture.md)
