"""
Tests for the Migration Runner.

This module tests migration script loading, execution, and batch processing.
"""

import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from nes.database.file_database import FileDatabase
from nes.services.migration import (
    Migration,
    MigrationManager,
    MigrationRunner,
    MigrationStatus,
)
from nes.services.publication.service import PublicationService
from nes.services.search.service import SearchService


@pytest.fixture
def temp_db():
    """Create a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "db"
        db = FileDatabase(db_path)
        yield db


@pytest.fixture
def services(temp_db):
    """Create service instances for testing."""
    publication = PublicationService(temp_db)
    search = SearchService(temp_db)

    return {
        "publication": publication,
        "search": search,
        "db": temp_db,
    }


@pytest.fixture
def temp_migrations_dir():
    """Create a temporary migrations directory with test migrations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        migrations_dir = Path(tmpdir) / "migrations"
        migrations_dir.mkdir()

        # Create a simple test migration
        migration_000 = migrations_dir / "000-test-migration"
        migration_000.mkdir()

        # Create migrate.py with metadata
        (migration_000 / "migrate.py").write_text(
            """
AUTHOR = "test@example.com"
DATE = "2024-01-20"
DESCRIPTION = "Test migration for unit tests"

async def migrate(context):
    context.log("Test migration executed")
    context.log("Migration completed")
"""
        )

        (migration_000 / "README.md").write_text("# Test Migration")

        yield migrations_dir


@pytest.fixture
def temp_db_repo():
    """Create a temporary database repository with Git."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_repo = Path(tmpdir) / "nes-db"
        db_repo.mkdir()

        # Initialize Git repository
        subprocess.run(["git", "init"], cwd=db_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=db_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=db_repo,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        (db_repo / "README.md").write_text("# Test Database\n")
        subprocess.run(
            ["git", "add", "."], cwd=db_repo, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=db_repo,
            check=True,
            capture_output=True,
        )

        yield db_repo


@pytest.mark.asyncio
async def test_create_context(services, temp_migrations_dir, temp_db_repo):
    """Test that migration context is created correctly."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo / "v2")
    runner = MigrationRunner(
        publication_service=services["publication"],
        search_service=services["search"],
        db=services["db"],
        migration_manager=manager,
    )

    migrations = await manager.discover_migrations()
    migration = migrations[0]

    context = runner.create_context(migration)

    assert context is not None
    assert context.publication == services["publication"]
    assert context.search == services["search"]
    assert context.db == services["db"]
    assert context.migration_dir == migration.folder_path


@pytest.mark.asyncio
async def test_load_script_success(services, temp_migrations_dir, temp_db_repo):
    """Test loading a valid migration script."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo / "v2")
    runner = MigrationRunner(
        publication_service=services["publication"],
        search_service=services["search"],
        db=services["db"],
        migration_manager=manager,
    )

    migrations = await manager.discover_migrations()
    migration = migrations[0]

    migrate_func, metadata = runner._load_script(migration)

    assert callable(migrate_func)
    assert metadata["author"] == "test@example.com"
    assert metadata["date"] == "2024-01-20"
    assert metadata["description"] == "Test migration for unit tests"


@pytest.mark.asyncio
async def test_load_script_missing_metadata(
    services, temp_migrations_dir, temp_db_repo
):
    """Test that loading a script without metadata fails."""
    # Create a migration without metadata
    migration_bad = temp_migrations_dir / "001-bad-migration"
    migration_bad.mkdir()

    (migration_bad / "migrate.py").write_text(
        """
async def migrate(context):
    pass
"""
    )

    manager = MigrationManager(temp_migrations_dir, temp_db_repo / "v2")
    runner = MigrationRunner(
        publication_service=services["publication"],
        search_service=services["search"],
        db=services["db"],
        migration_manager=manager,
    )

    migrations = await manager.discover_migrations()
    bad_migration = [m for m in migrations if m.name == "bad-migration"][0]

    with pytest.raises(ValueError, match="missing required metadata"):
        runner._load_script(bad_migration)


@pytest.mark.asyncio
async def test_run_migration_success(services, temp_migrations_dir, temp_db_repo):
    """Test running a migration successfully."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo / "v2")
    runner = MigrationRunner(
        publication_service=services["publication"],
        search_service=services["search"],
        db=services["db"],
        migration_manager=manager,
    )

    # Mock _get_git_diff to always return None (clean state) for tests
    runner._get_git_diff = lambda: None

    migrations = await manager.discover_migrations()
    migration = migrations[0]

    result = await runner.run_migration(migration)

    assert result.status == MigrationStatus.COMPLETED
    assert result.duration_seconds > 0
    assert len(result.logs) == 2
    assert "Test migration executed" in result.logs[0]
    assert result.error is None


@pytest.mark.asyncio
async def test_run_migration_skipped(services, temp_migrations_dir, temp_db_repo):
    """Test that already-applied migrations are skipped."""
    # Mark migration as applied by creating a migration log
    log_dir = temp_db_repo / "v2" / "migration-logs" / "000-test-migration"
    log_dir.mkdir(parents=True, exist_ok=True)

    import json

    metadata = {
        "migration_name": "000-test-migration",
        "status": "completed",
        "executed_at": "2024-11-09T10:00:00",
    }
    (log_dir / "metadata.json").write_text(json.dumps(metadata))

    # Commit the migration log so git diff is clean
    subprocess.run(
        ["git", "add", "."], cwd=temp_db_repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add migration log"],
        cwd=temp_db_repo,
        check=True,
        capture_output=True,
    )

    manager = MigrationManager(temp_migrations_dir, temp_db_repo / "v2")
    runner = MigrationRunner(
        publication_service=services["publication"],
        search_service=services["search"],
        db=services["db"],
        migration_manager=manager,
    )

    migrations = await manager.discover_migrations()
    migration = migrations[0]

    result = await runner.run_migration(migration)

    assert result.status == MigrationStatus.SKIPPED
    assert "already applied" in result.logs[0]


# Force flag removed - migrations are automatically skipped if already applied
