"""
Tests for new migration features:
- Migration log storage
- Git diff capture
- Clean state checking
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from nes.services.migration import MigrationManager, MigrationRunner, MigrationStatus
from nes.services.migration.models import Migration, MigrationResult


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
        (db_repo / "README.md").write_text("# Test Database")
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
async def test_migration_log_storage(temp_db_repo):
    """Test that migration logs are stored correctly."""
    from datetime import datetime

    # Create a mock migration
    migration = Migration(
        prefix=0,
        name="test-migration",
        folder_path=Path("/tmp/test"),
        script_path=Path("/tmp/test/migrate.py"),
        readme_path=None,
        author="test@example.com",
        date=datetime(2024, 11, 9),
        description="Test migration",
    )

    # Create a mock result
    result = MigrationResult(
        migration=migration,
        status=MigrationStatus.COMPLETED,
        duration_seconds=1.5,
        entities_created=10,
        relationships_created=5,
        error=None,
        logs=["Migration started", "Migration completed"],
    )

    # Create a minimal runner just to test log storage
    from nes.database.file_database import FileDatabase
    from nes.services.publication import PublicationService
    from nes.services.search import SearchService

    db = FileDatabase(base_path=str(temp_db_repo / "v2"))
    manager = MigrationManager(Path("/tmp"), temp_db_repo / "v2")

    runner = MigrationRunner(
        publication_service=PublicationService(database=db),
        search_service=SearchService(database=db),
        db=db,
        migration_manager=manager,
    )

    # Store the log
    await runner._store_migration_log(migration, result, git_diff="test diff content")

    # Verify log directory was created
    log_dir = temp_db_repo / "v2" / "migration-logs" / "000-test-migration"
    assert log_dir.exists()

    # Verify metadata.json
    metadata_file = log_dir / "metadata.json"
    assert metadata_file.exists()

    with open(metadata_file) as f:
        metadata = json.load(f)

    assert metadata["migration_name"] == "000-test-migration"
    assert metadata["author"] == "test@example.com"
    assert metadata["status"] == "completed"
    assert metadata["changes"]["entities_created"] == 10
    assert metadata["changes"]["relationships_created"] == 5
    assert metadata["changes"]["versions_created"] == 0  # Default value
    assert metadata["changes"]["has_diff"] is True

    # Verify changes.diff
    diff_file = log_dir / "changes.diff"
    assert diff_file.exists()
    assert diff_file.read_text() == "test diff content"

    # Verify logs.txt
    logs_file = log_dir / "logs.txt"
    assert logs_file.exists()
    logs_content = logs_file.read_text()
    assert "Migration started" in logs_content
    assert "Migration completed" in logs_content


@pytest.mark.asyncio
async def test_git_diff_capture(temp_db_repo):
    """Test that git diff is captured correctly."""
    from nes.database.file_database import FileDatabase
    from nes.services.publication import PublicationService
    from nes.services.search import SearchService

    db = FileDatabase(base_path=str(temp_db_repo / "v2"))
    manager = MigrationManager(Path("/tmp"), temp_db_repo / "v2")

    runner = MigrationRunner(
        publication_service=PublicationService(database=db),
        search_service=SearchService(database=db),
        db=db,
        migration_manager=manager,
    )

    # Create an uncommitted file
    test_file = temp_db_repo / "v2" / "test.json"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text('{"test": true}')

    # Get diff
    diff = runner._get_git_diff()

    # Should capture the new file
    assert diff is not None
    assert "test.json" in diff
    assert '{"test": true}' in diff


@pytest.mark.asyncio
async def test_clean_state_check_passes(temp_db_repo):
    """Test that clean state check passes when no uncommitted changes."""
    from nes.database.file_database import FileDatabase
    from nes.services.publication import PublicationService
    from nes.services.search import SearchService

    db = FileDatabase(base_path=str(temp_db_repo / "v2"))
    manager = MigrationManager(Path("/tmp"), temp_db_repo / "v2")

    runner = MigrationRunner(
        publication_service=PublicationService(database=db),
        search_service=SearchService(database=db),
        db=db,
        migration_manager=manager,
    )

    # Check clean state (should be clean after initial commit)
    is_clean = runner._check_clean_state()
    assert is_clean is True


@pytest.mark.asyncio
async def test_clean_state_check_fails(temp_db_repo):
    """Test that clean state check fails when there are uncommitted changes."""
    from nes.database.file_database import FileDatabase
    from nes.services.publication import PublicationService
    from nes.services.search import SearchService

    db = FileDatabase(base_path=str(temp_db_repo / "v2"))
    manager = MigrationManager(Path("/tmp"), temp_db_repo / "v2")

    runner = MigrationRunner(
        publication_service=PublicationService(database=db),
        search_service=SearchService(database=db),
        db=db,
        migration_manager=manager,
    )

    # Create an uncommitted file
    test_file = temp_db_repo / "v2" / "test.json"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text('{"test": true}')

    # Check clean state (should fail)
    is_clean = runner._check_clean_state()
    assert is_clean is False


@pytest.mark.asyncio
async def test_version_file_counting(temp_db_repo):
    """Test that version files are counted correctly, including nested directories."""
    from nes.database.file_database import FileDatabase
    from nes.services.publication import PublicationService
    from nes.services.search import SearchService

    db = FileDatabase(base_path=str(temp_db_repo / "v2"))
    manager = MigrationManager(Path("/tmp"), temp_db_repo / "v2")

    runner = MigrationRunner(
        publication_service=PublicationService(database=db),
        search_service=SearchService(database=db),
        db=db,
        migration_manager=manager,
    )

    # Initially should have 0 version files
    count_before = runner._count_version_files()
    assert count_before == 0

    # Create version files in nested directories (mimicking real structure)
    version_dir = temp_db_repo / "v2" / "version"

    # Create nested structure: version/entity/person/
    person_dir = version_dir / "entity" / "person"
    person_dir.mkdir(parents=True, exist_ok=True)

    (person_dir / "version1.json").write_text('{"version": 1}')
    (person_dir / "version2.json").write_text('{"version": 2}')

    # Create nested structure: version/relationship/member-of/
    relationship_dir = version_dir / "relationship" / "member-of"
    relationship_dir.mkdir(parents=True, exist_ok=True)

    (relationship_dir / "version1.json").write_text('{"version": 1}')

    # Should now count 3 version files across nested directories
    count_after = runner._count_version_files()
    assert count_after == 3


@pytest.mark.asyncio
async def test_migration_blocked_by_dirty_state(temp_db_repo):
    """Test that migrations are blocked when database has uncommitted changes."""
    from nes.database.file_database import FileDatabase
    from nes.services.publication import PublicationService
    from nes.services.search import SearchService

    # Create a test migration
    temp_migrations = Path(tempfile.mkdtemp())
    migration_dir = temp_migrations / "000-test-migration"
    migration_dir.mkdir(parents=True)

    (migration_dir / "migrate.py").write_text(
        """
AUTHOR = "test@example.com"
DATE = "2024-11-09"
DESCRIPTION = "Test migration"

async def migrate(context):
    context.log("Test migration")
"""
    )

    db = FileDatabase(base_path=str(temp_db_repo / "v2"))
    manager = MigrationManager(temp_migrations, temp_db_repo / "v2")

    runner = MigrationRunner(
        publication_service=PublicationService(database=db),
        search_service=SearchService(database=db),
        db=db,
        migration_manager=manager,
    )

    # Create an uncommitted file to make state dirty
    test_file = temp_db_repo / "v2" / "test.json"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text('{"test": true}')

    # Try to run migration
    migrations = await manager.discover_migrations()
    result = await runner.run_migration(migrations[0])

    # Should fail due to dirty state
    assert result.status == MigrationStatus.FAILED
    assert "uncommitted changes" in str(result.error).lower()
