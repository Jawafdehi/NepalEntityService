# Database Setup Guide

## Overview

The Nepal Entity Service uses a file-based database. The database is managed in a separate repository ([NepalEntityService-database](https://github.com/NewNepal-org/NepalEntityService-database)). You must clone it locally and set its path via an environment variable.

## Configuration

### Environment Variables

The database path is configured via the `NES_DB_URL` environment variable. Two protocols are supported:

#### `file://` - Standard File Database

Standard read-write file-based database:

```bash
# .env file
NES_DB_URL=file:///absolute/path/to/nes-db/v2
```

#### `file+memcached://` - In-Memory Cached Read-Only Database

For read-only workloads with high performance requirements, use the in-memory cached database. This loads all entities and relationships into memory at startup:

```bash
# .env file
NES_DB_URL=file+memcached:///absolute/path/to/nes-db/v2
```

**Benefits:**
- ⚡ Extremely fast read operations (no disk I/O)
- 🔒 Read-only safety (prevents accidental writes)
- 📦 Full dataset cached in memory

**Use Cases:**
- Production read-only API servers
- Search and query services
- High-traffic public endpoints

**Important:** 
- The path must be absolute (starting from filesystem root `/`)
- Write operations will raise `ValueError` with in-memory cached database
- Memory usage scales with database size

#### Examples

**Local Development (macOS/Linux):**
```bash
# Standard file database
NES_DB_URL=file:///Users/username/projects/NepalEntityService/nes-db/v2

# In-memory cached (read-only)
NES_DB_URL=file+memcached:///Users/username/projects/NepalEntityService/nes-db/v2
```

**Local Development (Windows):**
```bash
# Standard file database
NES_DB_URL=file:///C:/Users/username/projects/NepalEntityService/nes-db/v2

# In-memory cached (read-only)
NES_DB_URL=file+memcached:///C:/Users/username/projects/NepalEntityService/nes-db/v2
```

**Docker Container:**
```bash
# Standard file database
NES_DB_URL=file:///app/nes-db/v2

# In-memory cached (read-only) - recommended for production
NES_DB_URL=file+memcached:///app/nes-db/v2
```

## Database Repository Setup

### Cloning the Database

Clone the database repository to a location of your choice:

```bash
# Recommended: Shallow clone for local development (faster)
git clone --depth 1 git@github.com:NewNepal-org/NepalEntityService-database.git ./nes-db

# Or full clone if you plan to contribute data changes:
git clone git@github.com:NewNepal-org/NepalEntityService-database.git ./nes-db
```

### Updating the Database

To pull the latest database changes:

```bash
cd nes-db
git pull origin main
cd ..
```

### Committing Database Changes

If you make changes to the database that should be shared:

```bash
# Navigate to the database repository
cd nes-db

# Commit and push changes
git add .
git commit -m "Update database"
git push origin main
```

## Docker Setup

The Dockerfile automatically fetches a shallow clone of the database during the build process to ensure the container has the necessary data to run. 

### Building with Docker

```bash
# Build the image
docker build -t nepal-entity-service .

# Run with default database (uses the clone fetched during build)
docker run -p 8195:8195 nepal-entity-service

# Run with custom local database path (mount volume)
docker run -p 8195:8195 \
  -v /path/to/your/local/nes-db/v2:/app/nes-db/v2 \
  -e NES_DB_URL=file:///app/nes-db/v2 \
  nepal-entity-service
```

## Directory Structure

```
NepalEntityService/
├── nes-db/                    # Separate database repository
│   ├── README.md              # Database repository README
│   └── v2/                    # Version 2 database files
│       ├── entities/          # Entity JSON files
│       ├── relationships/     # Relationship JSON files
│       ├── versions/          # Version history
│       └── authors/           # Author records
├── nes/                      # Application code
│   └── config.py              # Configuration with DATABASE_URL support
└── .env                       # Local environment configuration
```

## Troubleshooting

### Database Repository Not Found

If you get a file not found error when starting the application, ensure you have cloned the database repository and properly set your `NES_DB_URL`:

```bash
git clone --depth 1 git@github.com:NewNepal-org/NepalEntityService-database.git ./nes-db
export NES_DB_URL=file://$(pwd)/nes-db/v2
```

### Permission Issues

Ensure the database directory has proper read/write permissions:

```bash
chmod -R 755 nes-db/v2
```

### Invalid NES_DB_URL

The `NES_DB_URL` must use the `file://` or `file+memcached://` protocol. If you see an error like:

```
ValueError: NES_DB_URL must use 'file://' or 'file+memcached://' protocol
```

Check that your URL starts with a supported protocol and uses an absolute path:

```bash
# ✅ Correct - standard file database
NES_DB_URL=file:///Users/username/projects/NepalEntityService/nes-db/v2

# ✅ Correct - in-memory cached database
NES_DB_URL=file+memcached:///Users/username/projects/NepalEntityService/nes-db/v2

# ❌ Wrong - missing protocol
NES_DB_URL=/Users/username/projects/NepalEntityService/nes-db/v2

# ❌ Wrong - relative path
NES_DB_URL=file://nes-db/v2

# ❌ Wrong - unsupported protocol
NES_DB_URL=postgres://localhost/nes-db
```

## Development Workflow

1. **Start with latest database:**
   ```bash
   cd nes-db && git pull origin main && cd ..
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env and SET NES_DB_URL to your absolute path!
   # Example: export NES_DB_URL=file://$(pwd)/nes-db/v2
   ```

3. **Run the service:**
   ```bash
   poetry run nes server dev
   ```

4. **Make database changes** through the API or CLI

5. **Commit database changes** (if needed):
   ```bash
   cd nes-db
   git add .
   git commit -m "Add new entities"
   git push
   cd ..
   ```
