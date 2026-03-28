# Migration System Architecture

This document describes the architecture of the Open Database Updates feature, which enables community contributions to the Nepal Entity Service through versioned migration folders. The system follows database migration patterns but applies them to data changes rather than schema changes.

## Table of Contents

1. [Overview](#overview)
2. [Two-Repository Architecture](#two-repository-architecture)
3. [Linear Migration Model](#linear-migration-model)
4. [Determinism Through Persisted Snapshots](#determinism-through-persisted-snapshots)
5. [Component Architecture](#component-architecture)
6. [Data Flow](#data-flow)
7. [Git Integration](#git-integration)
8. [Performance Considerations](#performance-considerations)
9. [Design Decisions](#design-decisions)

---

## Overview

The Open Database Updates feature introduces a migration-based system for managing data evolution in the Nepal Entity Service. This system enables community contributions through versioned migration folders that contain executable Python scripts and supporting data files.

### Key Concepts

- **Migration**: A versioned folder containing a Python script and supporting files that applies specific data changes
- **Linear Model**: Migrations execute in sequential order based on numeric prefixes
- **Determinism**: Once executed, migrations create logs that prevent re-execution
- **Two-Repository**: Application code and data are managed in separate Git repositories
- **Log-Based Tracking**: Migration history is tracked through log directories in the database

### Design Goals

1. **Community Contributions**: Enable anyone to propose data updates via GitHub pull requests
2. **Data Provenance**: Track the source and reasoning behind every data change
3. **Reproducibility**: Ensure database state can be recreated by replaying migrations
4. **Transparency**: Maintain complete audit trail through Git history
5. **Scalability**: Handle large databases (100k-1M files) efficiently

---

## Two-Repository Architecture

The system operates across two GitHub repositories to separate application code from data:

### Service API Repository

**Repository**: https://github.com/Jawafdehi/NepalEntityService

**Contents**:
- Application code (Python packages, API, CLI)
- Migration scripts in `migrations/` directory
- Documentation and tests
- Configuration files

**Characteristics**:
- Lightweight (~10MB)
- Fast to clone and develop
- Contains code, not data
- Contributors submit PRs here

**Structure**:
```
NepalEntityService/
├── migrations/
│   ├── 000-initial-locations/
│   │   ├── migrate.py
│   │   ├── README.md
│   │   └── locations.csv
│   ├── 001-political-parties/
│   │   ├── migrate.py
│   │   ├── README.md
│   │   └── parties.json
│   └── 002-update-names/
│       ├── migrate.py
│       └── README.md
├── nes/
│   ├── services/
│   │   └── migration/
│   │       ├── manager.py
│   │       ├── runner.py
│   │       ├── context.py
│   │       └── models.py
│   └── ...
├── nes-db/  (Separate Git repository)
└── ...
```

### Database Repository

**Repository**: https://github.com/Jawafdehi/NepalEntityService-database

**Contents**:
- Entity JSON files (100k-1M files)
- Relationship JSON files
- Version history files
- Author files

**Characteristics**:
- Large (~1GB+)
- Managed as separate Git repository at `nes-db/`
- Modified by migration execution
- Not directly edited by contributors

**Structure**:
```
nes-db/
├── v2/
│   ├── entity/
│   │   ├── person/
│   │   │   ├── ram-chandra-poudel.json
│   │   │   ├── sher-bahadur-deuba.json
│   │   │   └── ... (100k+ files)
│   │   ├── organization/
│   │   │   └── political_party/
│   │   │       └── nepali-congress.json
│   │   └── location/
│   │       └── province/
│   │           └── bagmati.json
│   ├── relationship/
│   │   └── ... (500k+ files)
│   ├── version/
│   │   └── entity/
│   │       └── person/
│   │           └── ram-chandra-poudel/
│   │               ├── v1.json
│   │               └── v2.json
│   └── author/
│       └── ... (1k+ files)
└── README.md
```

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    Contributor                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         1. Create migration in Service API Repo              │
│            migrations/005-add-ministers/                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         2. Submit PR to Service API Repo                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Maintainer                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         3. Review and merge PR                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         4. Execute migration locally                         │
│            nes migration run 005-add-ministers               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         5. Migration modifies Database Repo                  │
│            Creates files in nes-db/v2/                       │
│            Creates migration log in migration-logs/          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         6. Maintainer reviews and commits changes            │
│            cd nes-db && git add . && git commit && git push  │
└─────────────────────────────────────────────────────────────┘
```

### Design Rationale

**Separation of Concerns**:
- Application code and data are managed independently
- Service API repo remains lightweight for fast development
- Database repo can grow to millions of files without affecting service development

**Review Process**:
- Migration code is reviewed separately from data changes
- Maintainers review the logic before execution
- Data changes are the result of executing reviewed code

**Performance**:
- Developers can clone Service API repo quickly
- Database repo can use different Git strategies (shallow clones, sparse checkout)
- Large data doesn't slow down code development

**Audit Trail**:
- Git history in Database repo provides complete data evolution history
- Each migration creates a commit with detailed metadata
- Rollback is possible using standard Git operations

---

## Linear Migration Model

Migrations execute in sequential order based on numeric prefixes, similar to database schema migrations (Flyway, Alembic, Django).

### Migration Naming Convention

```
NNN-descriptive-name/
```

- **NNN**: Three-digit numeric prefix (000, 001, 002, ...)
- **descriptive-name**: Kebab-case description of the migration

**Examples**:
- `000-initial-locations`
- `001-political-parties`
- `002-update-party-leadership`
- `003-add-cabinet-ministers`

### Sequential Execution

Migrations are discovered and executed in order:

```python
# Migration Manager discovers migrations
migrations = [
    Migration(prefix=0, name="initial-locations", ...),
    Migration(prefix=1, name="political-parties", ...),
    Migration(prefix=2, name="update-party-leadership", ...),
]

# Migrations execute in order
for migration in migrations:
    if not is_applied(migration):
        execute(migration)
```

### Benefits of Linear Model

**Predictability**:
- Database state is deterministic based on which migrations have run
- No branching or merging of migration paths
- Clear progression of database evolution

**Simplicity**:
- Easy to understand and reason about
- No complex dependency resolution
- Straightforward rollback (revert commits in reverse order)

**Reproducibility**:
- Running migrations 000-005 always produces the same database state
- New environments can be bootstrapped by running all migrations
- Historical states can be recreated by running migrations up to a point

### Handling Conflicts

When multiple contributors create migrations simultaneously:

1. **First merged wins**: First PR to merge gets the next prefix number
2. **Second contributor rebases**: Updates their migration prefix to next available
3. **No conflicts**: Migrations are independent folders, no merge conflicts

**Example**:
```bash
# Contributor A creates 005-add-ministers
# Contributor B creates 005-add-parties (same prefix)

# Maintainer merges A's PR first
# B's PR now conflicts

# B updates their migration:
mv migrations/005-add-parties migrations/006-add-parties
# Update all references to 006 in migrate.py and README.md
# Push update to PR
```

---

## Determinism Through Migration Logs

A key design principle is that migrations are deterministic: running a migration multiple times produces the same result (no-op after first execution).

### The Problem

Without determinism:
- Re-running migrations creates duplicate entities
- Accidental re-execution corrupts data
- Difficult to recover from failures
- Unclear which migrations have been applied

### The Solution: Migration Logs

When a migration executes, a detailed log is stored in the database directory. This log serves as proof that the migration was applied and provides a complete audit trail.

**Key Concept**: Migration logs in `nes-db/v2/migration-logs/` track which migrations have been applied. Each migration creates a folder with metadata, git diff, and execution logs.

### How It Works

```python
class MigrationRunner:
    async def run_migration(self, migration: Migration):
        """Execute a migration and store logs."""
        
        # 1. Check for uncommitted changes (clean state requirement)
        if self._get_git_diff():
            raise RuntimeError("Database has uncommitted changes")
        
        # 2. Check if migration already applied
        if await self._is_migration_logged(migration):
            print(f"Migration {migration.full_name} already applied, skipping")
            return MigrationResult(status=MigrationStatus.SKIPPED)
        
        # 3. Execute migration script
        context = self.create_context(migration)
        await migration.script.migrate(context)
        
        # 4. Capture git diff of changes
        git_diff = self._get_git_diff()
        
        # 5. Store migration log
        await self._store_migration_log(migration, result, git_diff)
        
        # 6. Now the migration is "applied" (log exists)
        return result
    
    async def _is_migration_logged(self, migration: Migration) -> bool:
        """Check if migration has been applied by looking for migration log."""
        
        # Check for metadata.json in migration log directory
        log_dir = self.manager.db_path / "migration-logs" / migration.full_name
        metadata_file = log_dir / "metadata.json"
        return metadata_file.exists()
```

### Migration Log Structure

Each migration execution creates a log directory in the Database Repository:

```
nes-db/v2/migration-logs/005-add-cabinet-ministers/
├── metadata.json      # Migration metadata and statistics
├── changes.diff       # Git diff of all changes made
└── logs.txt          # Execution logs
```

**metadata.json**:
```json
{
  "migration_name": "005-add-cabinet-ministers",
  "author": "contributor@example.com",
  "date": "2024-03-15",
  "description": "Import current cabinet ministers",
  "executed_at": "2024-03-15T10:30:00",
  "duration_seconds": 12.3,
  "status": "completed",
  "changes": {
    "entities_created": 25,
    "relationships_created": 25,
    "versions_created": 50,
    "summary": "Created 25 entities, 25 relationships, and 50 versions",
    "has_diff": true
  }
}
```

**This log represents**:
1. **Tracking Record**: Proof that migration 005 was applied
2. **Audit Trail**: Who, what, when, and how many changes
3. **Change Details**: Complete git diff of all file changes
4. **Execution History**: Full logs from migration execution

### Clean State Requirement

Before running any migration, the system verifies that the database has no uncommitted changes:

```python
# Check for uncommitted changes
git_diff = self._get_git_diff()
if git_diff:
    raise RuntimeError(
        "Cannot run migration: Database has uncommitted changes. "
        "Please commit or stash changes before running migrations."
    )
```

**Why This Matters**:
- Ensures migration changes are isolated and trackable
- Prevents mixing migration changes with manual edits
- Makes git diff in migration logs accurate
- Allows clean rollback if migration fails

### Benefits

**Determinism**:
- Running `nes migration run --all` multiple times is safe
- First run executes pending migrations
- Subsequent runs skip already-applied migrations (detect logs)

**Idempotency**:
- Migrations can be written to be idempotent (check before create)
- System-level idempotency through log detection
- No duplicate entities from accidental re-execution

**Data Integrity**:
- Prevents corruption from re-running migrations
- Clear separation between applied and pending migrations
- Clean state requirement ensures isolated changes

**Audit Trail**:
- Complete git diff of all changes in changes.diff
- Detailed statistics (entities, relationships, versions created)
- Execution logs for debugging
- Metadata with author, date, duration

**Transparency**:
- Migration logs are human-readable JSON
- Git diff shows exactly what files changed
- No hidden state or tracking database

### Comparison to Traditional Tracking

**Traditional Approach** (separate tracking table):
```
migrations_applied:
  - id: 1, name: "000-initial-locations", applied_at: "2024-01-01"
  - id: 2, name: "001-political-parties", applied_at: "2024-01-15"
```

**Problems**:
- Tracking table can get out of sync with actual data
- Requires separate database for tracking
- Rollback requires updating both data and tracking table
- Not distributed (each environment has own tracking)

**Our Approach** (migration logs):
```
Migration logs in Database Repository:
  nes-db/v2/migration-logs/
    000-initial-locations/
      metadata.json
      changes.diff
      logs.txt
    001-political-parties/
      metadata.json
      changes.diff
      logs.txt
```

**Benefits**:
- Logs stored alongside data (always in sync)
- No separate tracking database needed
- Complete audit trail with git diffs
- Distributed via Git (pull to see applied migrations)
- Human-readable JSON format

---

## Component Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Interface                             │
│  nes migration list [--pending] [--json]                   │
│  nes migration run [name] [--all]                          │
│  nes migration create <name>                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Migration Manager                           │
│  • Discover migrations in migrations/ directory             │
│  • Check applied migrations (query Git log)                 │
│  • Determine pending migrations                             │
│  • Validate migration structure                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Migration Runner                            │
│  • Load migration script                                    │
│  • Create migration context                                 │
│  • Execute migration                                        │
│  • Handle errors and logging                                │
│  • Commit and push (persist snapshot)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Migration Context                           │
│  • Thin API for migration scripts                           │
│  • Access to Publication Service                            │
│  • Access to Search Service                                 │
│  • Access to Scraping Service                               │
│  • File reading helpers                                     │
│  • Logging mechanism                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Publication Service                         │
│  • Create/update entities                                   │
│  • Create/update relationships                              │
│  • Automatic versioning                                     │
│  • Write to Database Repository                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Database Repository (nes-db/)                   │
│  • Entity JSON files                                        │
│  • Relationship JSON files                                  │
│  • Version history files                                    │
│  • Git history (migration tracking)                         │
└─────────────────────────────────────────────────────────────┘
```

### Component Details

#### Migration Manager

**Responsibility**: Discovery and tracking of migrations

**Key Operations**:
- Scan `migrations/` directory for migration folders
- Validate migration structure (has migrate.py, README.md)
- Query Git log in Database Repository for applied migrations
- Compare discovered vs applied to find pending migrations
- Cache results to avoid repeated Git queries

**Interface**:
```python
class MigrationManager:
    async def discover_migrations(self) -> List[Migration]
    async def get_applied_migrations(self) -> List[str]
    async def get_pending_migrations(self) -> List[Migration]
    async def is_migration_applied(self, migration: Migration) -> bool
```

#### Migration Runner

**Responsibility**: Execution of migration scripts

**Key Operations**:
- Load migration script dynamically (import migrate.py)
- Create execution context with service access
- Execute migration script's `migrate()` function
- Track execution time and statistics
- Handle errors gracefully
- Commit changes to Database Repository (persist snapshot)
- Push to remote

**Interface**:
```python
class MigrationRunner:
    async def run_migration(
        self,
        migration: Migration
    ) -> MigrationResult
    
    async def run_migrations(
        self,
        migrations: List[Migration],
        stop_on_failure: bool = True
    ) -> List[MigrationResult]
    
    async def _store_migration_log(
        self,
        migration: Migration,
        result: MigrationResult,
        git_diff: Optional[str]
    ) -> None
```

#### Migration Context

**Responsibility**: Provide minimal API for migration scripts

**Key Operations**:
- Expose services (publication, search, scraping)
- Provide file reading helpers (CSV, JSON, Excel)
- Provide logging mechanism
- Provide migration folder path

**Design Philosophy**: Thin wrapper, no business logic

**Interface**:
```python
class MigrationContext:
    # Services
    publication: PublicationService
    search: SearchService
    scraping: ScrapingService
    db: EntityDatabase
    
    # Helpers
    def read_csv(self, filename: str) -> List[Dict[str, Any]]
    def read_json(self, filename: str) -> Any
    def read_excel(self, filename: str, sheet_name: str = None) -> List[Dict[str, Any]]
    def log(self, message: str) -> None
    
    # Properties
    @property
    def migration_dir(self) -> Path
```

---

## Data Flow

### Migration Execution Flow

```
1. User runs: nes migration run 005-add-ministers
                              │
                              ▼
2. CLI calls Migration Manager
   - Discover migration 005
   - Check if already applied (check for migration log)
                              │
                              ▼
3. Migration Runner checks clean state
   - Verify no uncommitted changes in nes-db/
   - Fail if dirty state detected
                              │
                              ▼
4. If not applied and clean, Migration Runner executes
   - Load migrate.py script
   - Create Migration Context
   - Count entities/relationships/versions before
                              │
                              ▼
5. Migration Runner executes migrate(context)
   - Script reads data files
   - Script calls context.publication.create_entity(...)
   - Script calls context.publication.create_relationship(...)
                              │
                              ▼
6. Publication Service writes to Database Repository
   - Creates entity JSON files in nes-db/v2/entity/
   - Creates relationship JSON files in nes-db/v2/relationship/
   - Creates version JSON files in nes-db/v2/version/
                              │
                              ▼
7. Migration Runner captures changes
   - Count entities/relationships/versions after
   - Capture git diff of all changes
                              │
                              ▼
8. Migration Runner stores migration log
   - Create nes-db/v2/migration-logs/005-add-ministers/
   - Write metadata.json (stats, author, date)
   - Write changes.diff (git diff output)
   - Write logs.txt (execution logs)
                              │
                              ▼
9. Migration is now "applied"
   - Migration log exists in nes-db/v2/migration-logs/
   - Re-running will skip (detect log)
   - User commits and pushes changes manually
```

### Read Flow (Checking Applied Migrations)

```
1. User runs: nes migration list --pending
                              │
                              ▼
2. Migration Manager discovers all migrations
   - Scan migrations/ directory
   - Parse folder names (NNN-descriptive-name)
   - Sort by prefix
                              │
                              ▼
3. Migration Manager checks applied migrations
   - Scan: nes-db/v2/migration-logs/
   - Check for metadata.json in each migration folder
   - Build list of applied migration names
                              │
                              ▼
4. Migration Manager compares
   - Discovered: [000, 001, 002, 003, 004, 005]
   - Applied: [000, 001, 002, 003]
   - Pending: [004, 005]
                              │
                              ▼
5. CLI displays pending migrations
   - 004-update-party-leadership
   - 005-add-cabinet-ministers
```

---

## Git Integration

### Manual Git Workflow

After running migrations, changes must be manually committed and pushed:

```bash
# 1. Run migration
nes migration run 005-add-cabinet-ministers

# 2. Review changes
cd nes-db
git status
git diff

# 3. Review migration log
cat v2/migration-logs/005-add-cabinet-ministers/metadata.json
cat v2/migration-logs/005-add-cabinet-ministers/changes.diff

# 4. Commit changes
git add .
git commit -m "Apply migration: 005-add-cabinet-ministers

Created 25 entities, 25 relationships, and 50 versions
See migration log for details"

# 5. Push to remote
git push origin main
```

**Why Manual Commits?**:
- Gives maintainers control over when changes are pushed
- Allows review of changes before committing
- Enables batching multiple migrations into one commit
- Provides flexibility in commit messages

### Querying Migration History

```bash
# See all applied migrations
ls nes-db/v2/migration-logs/

# See details of specific migration
cat nes-db/v2/migration-logs/005-add-cabinet-ministers/metadata.json

# See what files changed
cat nes-db/v2/migration-logs/005-add-cabinet-ministers/changes.diff

# See execution logs
cat nes-db/v2/migration-logs/005-add-cabinet-ministers/logs.txt
```

### Rollback

To rollback a migration:

```bash
# 1. Delete the migration log
rm -rf nes-db/v2/migration-logs/005-add-cabinet-ministers/

# 2. Revert the data changes
cd nes-db
git revert <commit-sha>

# 3. Commit the rollback
git add .
git commit -m "Rollback migration: 005-add-cabinet-ministers"
git push origin main

# 4. Migration can now be re-executed
nes migration run 005-add-cabinet-ministers
```

---

## Performance Considerations

### Large Database Repository (100k-1M files)

**Challenges**:
- Git performance degrades with many files
- Clone times become prohibitive
- Disk space requirements increase

**Solutions**:

**1. Shallow Clones**:
```bash
git clone --depth 1 https://github.com/org/nes-db.git
```

**2. Sparse Checkout**:
```bash
git clone --filter=blob:none --sparse https://github.com/org/nes-db.git
cd nes-db
git sparse-checkout set v2/entity/person
```

**3. Git Configuration**:
```bash
git config core.preloadindex true
git config core.fscache true
git config gc.auto 256
```

**4. Batch Commits**:
- Automatically split large commits
- 1000 files per commit
- Reduces Git overhead

### Migration Execution Performance

**Optimizations**:
- Async I/O for file operations
- Batch entity creation where possible
- Minimal validation (services handle it)
- Progress logging for long-running migrations

### Caching

**Applied Migrations Cache**:
```python
class MigrationManager:
    def __init__(self):
        self._applied_cache = None  # Cache Git query results
    
    async def get_applied_migrations(self):
        if self._applied_cache is not None:
            return self._applied_cache
        
        # Query Git log (expensive)
        result = subprocess.run(["git", "log", ...])
        
        # Cache result
        self._applied_cache = parse_result(result)
        return self._applied_cache
```

---

## Design Decisions

### Why Two Repositories?

**Decision**: Separate Service API and Database repositories

**Rationale**:
- **Performance**: Service API repo stays lightweight (~10MB)
- **Scalability**: Database repo can grow to 1GB+ without affecting development
- **Review Process**: Code review separate from data changes
- **Flexibility**: Different Git strategies for each repo

**Alternatives Considered**:
- Single repository: Would become huge and slow
- Database in separate storage (S3): Loses Git benefits (history, rollback)

### Why Linear Migration Model?

**Decision**: Sequential migrations with numeric prefixes

**Rationale**:
- **Simplicity**: Easy to understand and reason about
- **Predictability**: Database state is deterministic
- **Reproducibility**: Running migrations 000-N always produces same state

**Alternatives Considered**:
- Branching migrations: Too complex, hard to merge
- Timestamp-based: Conflicts when multiple contributors work simultaneously
- Dependency graph: Overkill for data migrations

### Why Migration Logs for Tracking?

**Decision**: Use log directories in database for migration tracking

**Rationale**:
- **Simplicity**: No separate tracking database needed
- **Transparency**: Human-readable JSON files
- **Audit Trail**: Complete git diff and execution logs
- **Flexibility**: Manual git commits give maintainers control

**Alternatives Considered**:
- Git commits as tracking: Too automatic, less control
- Separate tracking table: Can get out of sync with data
- External database: Adds complexity and sync issues

### Why Thin Migration Context?

**Decision**: Minimal API, direct service access

**Rationale**:
- **Simplicity**: Less code to maintain
- **Flexibility**: Migration scripts can use full service APIs
- **Transparency**: No hidden behavior or magic

**Alternatives Considered**:
- Rich context with helpers: More maintenance burden
- Wrapper methods: Hides service capabilities
- DSL for migrations: Too restrictive

### Why File-Based Storage?

**Decision**: JSON files instead of traditional database

**Rationale**:
- **Git-Friendly**: Human-readable, easy to diff
- **Transparency**: Can inspect files directly
- **Simplicity**: No database server needed
- **Versioning**: Git provides version control

**Alternatives Considered**:
- PostgreSQL: Requires server, harder to version
- MongoDB: Same issues as PostgreSQL
- SQLite: Better, but still not as Git-friendly

---

## Additional Resources

- **Contributor Guide**: See [Migration Contributor Guide](/contributors/migration-contributor-guide) for creating migrations
- **Maintainer Guide**: See [Migration Maintainer Guide](/contributors/migration-maintainer-guide) for executing migrations
- **API Reference**: See [OpenAPI documentation](/docs) for complete API documentation
- **Data Models**: See [Data Models](/consumers/data-models) for entity schemas

---

**Last Updated:** 2024
**Version:** 2.0
