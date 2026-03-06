# Contributor Guide

This guide is for developers who want to contribute to the Nepal Entity Service project, run their own instance, or maintain data locally.

## Prerequisites

- Python 3.12+
- Poetry (Python package manager)
- Git
- Basic understanding of Python and REST APIs

## Getting Started

### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/NewNepal-org/NepalEntityService.git
cd NepalEntityService

# Clone the database repository and set NES_DB_URL
git clone --depth 1 https://github.com/NewNepal-org/NepalEntityService-database.git ./nes-db
export NES_DB_URL=file://$(pwd)/nes-db/v2
```

### 2. Install Dependencies

```bash
# Install with Poetry
poetry install

# Install with API extras (for running the server)
poetry install --extras api

# Install with all extras (API + scraping)
poetry install --extras all
```

### 3. Set Up the Database

The database is managed in a separate Git repository. See the [Database Setup](/contributors/database-setup) guide for detailed configuration.

```bash
# Verify the database
ls -la nes-db/v2/

# Set the database path (required)
export NES_DB_URL=file:///absolute/path/to/nes-db/v2
```

## Project Structure

```
NepalEntityService/
├── nes/                          # Main package
│   ├── models/                   # Data models (Entity, Relationship, etc.)
│   ├── database/                 # Database layer (FileDatabase)
│   ├── services/                 # Business logic (Publication, Search)
│   ├── api/                      # FastAPI application
│   ├── cli/                      # Command-line interface
│   ├── scraping/                 # Web scraping and data collection
│   └── config.py                 # Configuration management
├── nes-db/                       # Database (Separate Git repository)
│   └── v2/                       # Version 2 database files
├── migrations/                   # Data migration scripts
├── docs/                         # Documentation
├── tests/                        # Test suite
├── examples/                     # Example scripts
├── notebooks/                    # Jupyter notebooks
└── pyproject.toml               # Poetry configuration
```

## CLI Commands

The `nes` CLI provides commands for managing the service:

### Server Commands

```bash
# Start production server
poetry run nes server start

# Start development server (with auto-reload)
poetry run nes server dev

# Alternative: Use the nes-dev shortcut for development
poetry run nes-dev

# Specify custom host/port
poetry run nes server start --host 0.0.0.0 --port 8080
```

### Migration Commands

```bash
# Run a migration
poetry run nes migration run <migration-name>

# List available migrations
poetry run nes migration list

# List pending migrations
poetry run nes migration list --pending
```

For detailed migration information, see:
- [Migration Contributor Guide](/contributors/migration-contributor-guide) - Creating migrations
- [Migration Maintainer Guide](/contributors/migration-maintainer-guide) - Reviewing and executing migrations
- [Migration Architecture](/contributors/migration-architecture) - System design

## Development Workflow

### Running the API Server

```bash
# Development mode with auto-reload
poetry run nes server dev

# Alternative: Use the nes-dev shortcut
poetry run nes-dev

# The API will be available at:
# - Documentation: http://localhost:8195/
# - API endpoints: http://localhost:8195/api/
# - OpenAPI docs: http://localhost:8195/docs
```

The `nes-dev` command is a convenient shortcut that starts the development server with live reload enabled. Any changes to the code will automatically restart the server, making it ideal for active development.

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=nes

# Run specific test file
poetry run pytest tests/services/test_publication_service.py
```

### Code Quality

```bash
# Format code with Black
poetry run black nes/ tests/

# Sort imports with isort
poetry run isort nes/ tests/

# Lint with flake8
poetry run flake8 nes/ tests/
```

## Data Maintenance

### Using the Publication Service

The Publication Service provides a Pythonic interface for maintaining data:

```python
from pathlib import Path
from nes.database.file_database import FileDatabase
from nes.services.publication import PublicationService

# Initialize services
db = FileDatabase(base_path="nes-db/v2")
pub_service = PublicationService(database=db)

# Create an entity
entity = await pub_service.create_entity(
    entity_data={
        "slug": "politician-name",
        "type": "person",
        "names": [{
            "kind": "PRIMARY",
            "en": {"full": "Full Name"},
            "ne": {"full": "पूरा नाम"}
        }]
    },
    author_id="author:human:your-name",
    change_description="Added new politician"
)

# Update an entity
entity.attributes["position"] = "Minister"
updated = await pub_service.update_entity(
    entity=entity,
    author_id="author:human:your-name",
    change_description="Updated position"
)
```

For detailed data maintenance, see the [Data Maintainer Guide](/contributors/data-maintainer-guide).

## Scraping Service

The scraping service automates data collection using GenAI/LLM:

### Prerequisites

```bash
# Install with scraping extras
poetry install --extras scraping

# Set up Google Cloud credentials (for Vertex AI)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### Using the Scraper

```python
from nes.services.scraping import WikipediaScraper, DataNormalizer

# Scrape Wikipedia
scraper = WikipediaScraper()
raw_data = await scraper.scrape_politician("Ram Chandra Poudel")

# Normalize to NES format
normalizer = DataNormalizer()
entity_data = await normalizer.normalize(raw_data)
```

## Creating Migrations

Migrations are the recommended way to contribute data changes:

### 1. Create Migration Structure

```bash
mkdir -p migrations/001-add-new-politicians
cd migrations/001-add-new-politicians
```

### 2. Create Required Files

```
001-add-new-politicians/
├── migrate.py          # Migration script
├── README.md           # Documentation
└── data/              # Optional: supporting data files
```

### 3. Implement Migration

```python
# migrate.py
from nes.services.publication import PublicationService

async def migrate(pub_service: PublicationService, dry_run: bool = False):
    """Add new politicians to the database."""
    
    # Create entities
    entity = await pub_service.create_entity(
        entity_data={...},
        author_id="author:human:contributor-name",
        change_description="Added via migration 001"
    )
    
    if dry_run:
        print(f"Would create entity: {entity.id}")
    else:
        print(f"Created entity: {entity.id}")
```

### 4. Submit Pull Request

See the [Migration Contributor Guide](/contributors/migration-contributor-guide) for the complete workflow.

## Contributing Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions focused and small

### Commit Messages

```
feat: Add new entity type for government bodies
fix: Correct relationship validation logic
docs: Update API guide with new endpoints
test: Add tests for search service
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes
6. Push to your fork
7. Open a Pull Request

## Package Extras

The project uses Poetry extras for optional dependencies:

```bash
# API only (FastAPI, Uvicorn)
poetry install --extras api

# Scraping only (Wikipedia, Google AI)
poetry install --extras scraping

# Everything
poetry install --extras all
```

## Environment Variables

```bash
# Database path (file:// protocol required)
export NES_DB_URL=file:///absolute/path/to/nes-db/v2

# API server configuration
export NES_HOST=0.0.0.0
export NES_PORT=8195

# Google Cloud (for scraping)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

## Docker Deployment

```bash
# Build image
docker build -t nepal-entity-service .

# Run container
docker run -p 8195:8195 nepal-entity-service

# Run with custom database
docker run -p 8195:8195 \
  -v /path/to/database:/app/nes-db/v2 \
  -e NES_DB_URL=file:///app/nes-db/v2 \
  nepal-entity-service
```

## Resources

### Documentation
- [API Consumer Guide](/consumers/api-guide) - Using the public API
- [Data Models](/consumers/data-models) - Entity and relationship schemas
- [Service Design](/specs/nepal-entity-service/design) - Architecture details
- [Database Setup](/contributors/database-setup) - Database repository configuration
- [Usage Examples](/contributors/usage-examples) - Code examples and notebooks

### Migration Guides
- [Migration Contributor Guide](/contributors/migration-contributor-guide) - Creating migrations
- [Migration Maintainer Guide](/contributors/migration-maintainer-guide) - Reviewing migrations
- [Migration Architecture](/contributors/migration-architecture) - System design

### Data Maintenance
- [Data Maintainer Guide](/contributors/data-maintainer-guide) - Local data maintenance
- [Examples](/consumers/examples) - Common usage patterns

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **GitHub Discussions**: Ask questions and share ideas
- **Pull Requests**: Contribute code or documentation

## License

This project is open source. See the LICENSE file for details.
