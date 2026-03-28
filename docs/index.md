Welcome to the **Nepal Entity Service** (NES) documentation. 🇳🇵 NES is an **Open Source, open data, and open API** project that provides a comprehensive platform for managing Nepali public entities including persons, organizations, and locations with full versioning and relationship tracking.

## Open Source • Open Data • Open API

Nepal Entity Service is built on three core principles:

- **🔓 Open Source**: The entire codebase is open source and available on [GitHub](https://github.com/Jawafdehi/NepalEntityService). Anyone can contribute, review, or run their own instance.

- **📊 Open Data**: All entity data is publicly accessible and maintained through transparent, community-driven migrations. Every change is tracked, reviewed, and versioned with complete audit trails. Learn more about [database update workflows](/contributors/workflows).

- **🌐 Open API**: A free, public REST API at [https://nes.jawafdehi.org/api](https://nes.jawafdehi.org/api) provides read access to all entity data without authentication. Build applications, conduct research, or integrate with your projects freely.

## Entities hosted

### Currently offering

1. Location data
    1. 7 Provinces (`location/province`)
    1. 77 Districts (`location/district`)
    1. 165 constituencies (`location/constituency`)
    1. 460 Rural municipalities (VDCs) (`location/rural_municipality`)
    1. 11 Sub-metropolitician cities (`location/sub_metropolitician_city`)
    1. 6 Metropolitan Cities (`location/metropolitan_city`)
    1. 276 Municipalities (`location/municipality`)
    1. 6,743 wards (`location/ward`)
2. Political Parties (`organization/political_party`)
    1. 151 registered political parties (Official data from National Election Commission)
3. Politicians (`person`)
    1. 7,744 party candidates from 2079 B.S. national and provincial elections.
4. Health Facilities (`organization/hospital`)
    1. 11,399 hospitals and health facilities from Nepal Health Facility Registry (NHFR)
5. 204 Government Bodies (`organization/government_body`)
6. 310 International organizations (`organization/international_org`)
7. 122 NGOs (`organization/ngo`)
8. 2,979 development projects (`project/development_project`)

### Near future plans
1. Incorporate newly registered political parties
1. Incorporate complete government bodies data at all levels
1. Incorporate current government leaders, and Nepali bureaucrats

## Documentation Index

### For API Consumers
Start here if you want to use the public Nepal Entity Service API:

- **[Getting Started](/consumers/getting-started)** - Quick start guide for using the API
- **[API Consumer Guide](/consumers/api-guide)** - Using the public API at https://nes.jawafdehi.org/api
- **[OpenAPI Documentation](https://nes.jawafdehi.org/docs)** - Interactive API reference
- **[Data Models](/consumers/data-models)** - Understanding entity and relationship schemas
- **[Examples](/consumers/examples)** - Common usage patterns and code examples

### For Contributors
Start here if you want to contribute to the project or run your own instance:

- **[Contributor Guide](/contributors/contributor-guide)** - Setup, development workflow, and contributing
- **[Database Setup](/contributors/database-setup)** - Git submodule and database configuration
- **[Usage Examples](/contributors/usage-examples)** - Code examples, notebooks, and learning paths

#### Data Maintenance & Migrations
For contributors who manage data and migrations:

- **[Database Workflows](/contributors/workflows)** - Overview of different maintenance and update workflows
- **[Data Maintainer Guide](/contributors/data-maintainer-guide)** - Local data maintenance with Publication Service
- **[Migration Contributor Guide](/contributors/migration-contributor-guide)** - Creating and submitting data migrations
- **[Migration Maintainer Guide](/contributors/migration-maintainer-guide)** - Reviewing and executing migrations
- **[Migration Architecture](/contributors/migration-architecture)** - Migration system design and workflow

#### Service Guides
Detailed guides for using the core services:

- **[Publication Service Guide](/contributors/publication-service-guide)** - Creating and updating entities and relationships
- **[Search Service Guide](/contributors/search-service-guide)** - Querying entities and relationships
- **[Scraping Service Guide](/contributors/scraping-service-guide)** - Extracting and normalizing data from external sources
- **[Translation Guide](/contributors/translation-guide)** - Translate between English and Nepali using the CLI

#### Specifications
Technical specifications and design documents:

- [Requirements](/specs/nepal-entity-service/requirements)
- [Design](/specs/nepal-entity-service/design)
- [Tasks](/specs/nepal-entity-service/tasks)

### All Documentation Files

#### Consumer Documentation
- [getting-started](/consumers/getting-started) - Quick start guide
- [api-guide](/consumers/api-guide) - API consumer guide
- [data-models](/consumers/data-models) - Entity schemas
- [examples](/consumers/examples) - Usage examples

#### Contributor Documentation
- [contributor-guide](/contributors/contributor-guide) - Contributor setup and workflow
- [database-setup](/contributors/database-setup) - Database configuration
- [usage-examples](/contributors/usage-examples) - Code examples and notebooks
- [workflows](/contributors/workflows) - Database maintenance and update workflows
- [data-maintainer-guide](/contributors/data-maintainer-guide) - Data maintenance guide
- [migration-architecture](/contributors/migration-architecture) - Migration system design
- [migration-contributor-guide](/contributors/migration-contributor-guide) - Creating migrations
- [migration-maintainer-guide](/contributors/migration-maintainer-guide) - Executing migrations
- [publication-service-guide](/contributors/publication-service-guide) - Publication Service API and usage
- [search-service-guide](/contributors/search-service-guide) - Search Service API and usage
- [scraping-service-guide](/contributors/scraping-service-guide) - Scraping Service API and usage
- [translation-guide](/contributors/translation-guide) - Translation CLI guide

## What is Nepal Entity Service?

The Nepal Entity Service provides a robust foundation for civic technology applications, built from the ground up with **multilingual support** and a deep commitment to **respecting Nepali culture in software**. The service offers:

- **Structured Entity Management**: Manage persons, organizations, and locations with rich metadata
- **Versioning System**: Complete audit trails for all changes with author attribution
- **Relationship Tracking**: Model complex connections between entities
- **Multilingual Support**: Native support for Nepali (Devanagari) and English, with proper handling of Nepali names, transliteration, and cultural context
- **RESTful API**: Public read-only API for accessing entity data
- **Data Maintainer Interface**: Pythonic interface for local data maintenance
- **Cultural Authenticity**: Designed to preserve and respect Nepali linguistic and cultural nuances in all aspects of the software

## Key Features

### Entity Management
Manage three types of entities with rich metadata:
- **Persons**: Politicians, public officials, and other public figures
- **Organizations**: Political parties, government bodies, NGOs
- **Locations**: Provinces, districts, municipalities, and wards

### Versioning and Audit Trails
Every change to entities and relationships is tracked with:
- Complete snapshots of previous states
- Author attribution and timestamps
- Change descriptions for transparency
- Historical state retrieval

### Relationship System
Model complex connections between entities:
- Typed relationships (MEMBER_OF, AFFILIATED_WITH, EMPLOYED_BY, etc.)
- Temporal relationships with start and end dates
- Bidirectional relationship queries
- Relationship versioning

### Multilingual Support & Cultural Respect
Built from the ground up to honor Nepal's linguistic and cultural context:
- **Native Nepali Support**: First-class support for Nepali (Devanagari) script alongside English
- **Proper Name Handling**: Authentic representation of Nepali names without forcing Western conventions
- **Transliteration & Romanization**: Accurate conversion between scripts while preserving meaning
- **Cross-Language Search**: Query entities in either Nepali or English seamlessly
- **Cultural Context Preservation**: Maintain authenticity to Nepali political, social, and organizational structures
- **Respectful Software Design**: Every aspect of the service is designed to respect and celebrate Nepali culture, not just accommodate it

## API Overview

The Nepal Entity Service provides a public read-only API for accessing entity data:

```
GET /api/entities              # Search and list entities
GET /api/entities/{id}         # Get specific entity
GET /api/relationships         # Query relationships
GET /api/entities/{id}/versions # Get version history
GET /api/schemas               # Discover entity types
GET /api/health                # Health check
```

All API endpoints are documented in the interactive [OpenAPI documentation](/docs).

## Use Cases

The Nepal Entity Service is designed for:

- **Civic Technology Applications**: Build transparency and accountability platforms
- **Research and Analysis**: Analyze political and organizational networks
- **Data Journalism**: Track relationships and changes over time
- **Government Transparency**: Provide public access to entity information
- **Academic Research**: Study Nepal's political and administrative structures

## Getting Started

Ready to start using the Nepal Entity Service? Check out the [Getting Started](/consumers/getting-started) guide for installation instructions and your first API calls.

## Project Status

Nepal Entity Service v2 is currently in active development as an open source, open data initiative.

### Open Access
- **Public API**: Free, read-only access at https://nes.jawafdehi.org/api
- **No Authentication Required**: Access all entity data without API keys or registration
- **Community Maintained**: Data updates through transparent migration workflow

### Open Contributions
- **Code Contributions**: Submit pull requests for features, fixes, or improvements
- **Data Contributions**: Propose data updates through the migration system
- **Community Review**: All changes are reviewed by maintainers before merging

## License and Contributing

This project is licensed under the **Hippocratic License 3.0**, an ethical source license that grants broad permissions to use, modify, and distribute the software, with one important condition: the software must not be used in ways that violate human rights laws or principles as defined by the United Nations Universal Declaration of Human Rights.

### What This Means

- ✅ **You can freely**: Use, copy, modify, merge, publish, distribute, sublicense, and sell the software
- ✅ **For any ethical purpose**: Research, civic technology, journalism, education, commercial applications
- ❌ **Not for**: Activities that violate human rights, including surveillance that violates privacy rights, discrimination, or other uses that conflict with internationally recognized human rights principles

### Why This License?

The Nepal Entity Service manages data about public figures and organizations. We chose the Hippocratic License to:

- **Promote ethical use**: Encourage applications that serve the public good
- **Prevent harm**: Discourage misuse for surveillance, harassment, or discrimination
- **Align with values**: Reflect our commitment to transparency and human rights

The license is designed to be permissive for legitimate uses while establishing clear ethical boundaries.

### Contributing

We welcome contributions from everyone who shares our commitment to ethical technology:

- **Developers**: Contribute code, fix bugs, add features
- **Data Contributors**: Submit migrations to add or update entity data
- **Researchers**: Use the data and API for academic research
- **Civic Technologists**: Build transparency and accountability applications

For more information about contributing, see our [Contributor Guide](/contributors/contributor-guide) or visit our [GitHub repository](https://github.com/Jawafdehi/NepalEntityService).

### Full License Text

The complete Hippocratic License 3.0 text is available in the [LICENSE](https://github.com/Jawafdehi/NepalEntityService/blob/main/LICENSE) file in the repository. For more information about the Hippocratic License, visit [firstdonoharm.dev](https://firstdonoharm.dev/).

---

**Need Help?** Check out our [Examples](/consumers/examples) page for common usage patterns, or explore the [OpenAPI documentation](/docs) for detailed endpoint documentation.
