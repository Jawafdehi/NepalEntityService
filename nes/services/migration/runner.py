"""
Migration Runner for executing migration scripts.

This module provides the MigrationRunner class which handles:
- Loading and executing migration scripts
- Creating migration contexts for script execution
- Tracking execution statistics (entities/relationships created)
- Error handling and logging
- Deterministic execution (checking for migration logs)
- Storing migration logs for tracking applied migrations
"""

import importlib.util
import inspect
import logging
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import List, Optional

from nes.database.entity_database import EntityDatabase
from nes.services.migration.context import MigrationContext
from nes.services.migration.manager import MigrationManager
from nes.services.migration.models import Migration, MigrationResult, MigrationStatus
from nes.services.publication.service import PublicationService
from nes.services.scraping.service import ScrapingService
from nes.services.search.service import SearchService

logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    Executes migration scripts and manages migration logs.

    The MigrationRunner is responsible for:
    - Loading migration scripts dynamically
    - Creating execution contexts with service access
    - Executing migration scripts with error handling
    - Tracking execution statistics
    - Checking for migration logs to ensure determinism
    - Storing migration logs for tracking applied migrations
    - Managing batch execution of multiple migrations
    """

    def __init__(
        self,
        publication_service: PublicationService,
        search_service: SearchService,
        scraping_service: ScrapingService,
        db: EntityDatabase,
        migration_manager: MigrationManager,
    ):
        """
        Initialize the Migration Runner.

        Args:
            publication_service: Service for creating/updating entities and relationships
            search_service: Service for searching and querying entities
            scraping_service: Service for data extraction and normalization
            db: Database for direct read access to entities
            migration_manager: Manager for discovering and tracking migrations
        """
        self.publication = publication_service
        self.search = search_service
        self.scraping = scraping_service
        self.db = db
        self.manager = migration_manager

        # Check if database directory is a git repository
        db_repo_path = self.manager.db_path.parent
        git_dir = db_repo_path / ".git"
        if not git_dir.exists():
            logger.warning(
                f"Database directory is not a git repository: {db_repo_path}. "
                "Migration change tracking will not include git diffs. "
                "Expected nes-db to be a git submodule."
            )

        logger.info("MigrationRunner initialized")

    def create_context(self, migration: Migration) -> MigrationContext:
        """
        Create execution context for migration script.

        The context provides the migration script with:
        - Access to publication, search, and scraping services
        - Access to the database for read operations
        - File reading helpers (CSV, JSON, Excel)
        - Logging mechanism
        - Path to the migration folder

        Args:
            migration: Migration to create context for

        Returns:
            MigrationContext instance ready for script execution

        Example:
            >>> runner = MigrationRunner(...)
            >>> migration = Migration(...)
            >>> context = runner.create_context(migration)
            >>> # Pass context to migration script
            >>> await migrate(context)
        """
        logger.debug(f"Creating context for migration {migration.full_name}")

        context = MigrationContext(
            publication_service=self.publication,
            search_service=self.search,
            scraping_service=self.scraping,
            db=self.db,
            migration_dir=migration.folder_path,
        )

        return context

    def _load_script(self, migration: Migration) -> tuple:
        """
        Load migration script dynamically and validate it.

        This method:
        - Dynamically imports the migration script (migrate.py or run.py)
        - Validates that the script has a migrate() function
        - Validates that the script has required metadata (AUTHOR, DATE, DESCRIPTION)
        - Handles syntax errors gracefully

        Args:
            migration: Migration to load script for

        Returns:
            Tuple of (migrate_function, metadata_dict)

        Raises:
            ValueError: If script is invalid or missing required components
            SyntaxError: If script has syntax errors

        Example:
            >>> runner = MigrationRunner(...)
            >>> migration = Migration(...)
            >>> migrate_func, metadata = runner._load_script(migration)
            >>> await migrate_func(context)
        """
        logger.debug(f"Loading script for migration {migration.full_name}")

        script_path = migration.script_path

        if not script_path.exists():
            raise ValueError(f"Migration script not found: {script_path}")

        # Create a unique module name to avoid conflicts
        module_name = f"migration_{migration.full_name.replace('-', '_')}"

        try:
            # Load the module dynamically
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            if spec is None or spec.loader is None:
                raise ValueError(f"Failed to load module spec from {script_path}")

            module = importlib.util.module_from_spec(spec)

            # Add to sys.modules temporarily to support relative imports
            sys.modules[module_name] = module

            try:
                spec.loader.exec_module(module)
            finally:
                # Clean up sys.modules
                if module_name in sys.modules:
                    del sys.modules[module_name]

            logger.debug(f"Successfully loaded module from {script_path}")

        except SyntaxError as e:
            error_msg = (
                f"Syntax error in migration script {migration.full_name}:\n"
                f"  File: {e.filename}\n"
                f"  Line {e.lineno}: {e.text}\n"
                f"  {' ' * (e.offset - 1) if e.offset else ''}^\n"
                f"  {e.msg}"
            )
            logger.error(error_msg)
            raise SyntaxError(error_msg)

        except Exception as e:
            error_msg = f"Failed to load migration script {migration.full_name}: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate that the module has a migrate() function
        if not hasattr(module, "migrate"):
            raise ValueError(
                f"Migration script {migration.full_name} must define a 'migrate()' function"
            )

        migrate_func = getattr(module, "migrate")

        # Validate that migrate is a function
        if not callable(migrate_func):
            raise ValueError(
                f"'migrate' in {migration.full_name} must be a callable function"
            )

        # Validate that migrate is async
        if not inspect.iscoroutinefunction(migrate_func):
            raise ValueError(
                f"'migrate()' function in {migration.full_name} must be async "
                "(defined with 'async def')"
            )

        # Extract metadata
        metadata = {
            "author": getattr(module, "AUTHOR", None),
            "date": getattr(module, "DATE", None),
            "description": getattr(module, "DESCRIPTION", None),
        }

        # Validate required metadata
        missing_metadata = []
        if not metadata["author"]:
            missing_metadata.append("AUTHOR")
        if not metadata["date"]:
            missing_metadata.append("DATE")
        if not metadata["description"]:
            missing_metadata.append("DESCRIPTION")

        if missing_metadata:
            raise ValueError(
                f"Migration script {migration.full_name} is missing required metadata: "
                f"{', '.join(missing_metadata)}"
            )

        logger.debug(
            f"Validated migration script {migration.full_name}: "
            f"author={metadata['author']}, date={metadata['date']}"
        )

        return migrate_func, metadata

    async def run_migration(
        self,
        migration: Migration,
    ) -> MigrationResult:
        """
        Execute a migration script with determinism check.

        This method:
        - Checks if migration already applied before execution
        - Skips execution if migration log exists (returns SKIPPED status)
        - Executes the migration script with proper context
        - Tracks execution time and statistics
        - Stores migration logs after successful execution
        - Handles all exceptions gracefully

        Args:
            migration: Migration to execute

        Returns:
            MigrationResult with execution details

        Example:
            >>> runner = MigrationRunner(...)
            >>> migration = Migration(...)
            >>> result = await runner.run_migration(migration)
            >>> print(result.status)
            MigrationStatus.COMPLETED
        """
        logger.info(f"Running migration {migration.full_name}")

        # Create result object
        result = MigrationResult(
            migration=migration,
            status=MigrationStatus.RUNNING,
        )

        # Check for uncommitted changes before running migration (unless disabled)
        git_diff_check_disabled = (
            os.getenv("NES_MIGRATIONS_GIT_DIFF_CHECK_DISABLED", "false").lower()
            == "true"
        )

        if not git_diff_check_disabled:
            existing_diff = self._get_git_diff()
            if existing_diff:
                error_msg = (
                    f"Cannot run migration {migration.full_name}: "
                    "Database has uncommitted changes. "
                    "Please commit or stash changes before running migrations."
                )
                logger.error(error_msg)
                result.status = MigrationStatus.FAILED
                result.error = RuntimeError(error_msg)
                result.logs.append(error_msg)
                return result
        else:
            logger.warning(
                f"Git diff check disabled for migration {migration.full_name} "
                "(NES_MIGRATIONS_GIT_DIFF_CHECK_DISABLED=true)"
            )

        # Check if migration already applied (determinism check via migration logs)
        is_applied = await self._is_migration_logged(migration)
        if is_applied:
            logger.info(
                f"Migration {migration.full_name} already applied "
                "(migration log exists), skipping"
            )
            result.status = MigrationStatus.SKIPPED
            result.logs.append(
                f"Migration {migration.full_name} already applied, skipping"
            )
            return result

        # Load migration script
        try:
            migrate_func, metadata = self._load_script(migration)
            logger.debug(f"Loaded migration script {migration.full_name}")
        except Exception as e:
            logger.error(f"Failed to load migration script: {e}")
            result.status = MigrationStatus.FAILED
            result.error = e
            result.logs.append(f"Failed to load migration script: {e}")
            return result

        # Create execution context
        context = self.create_context(migration)

        # Track statistics before execution
        entities_before = await self._count_entities()
        relationships_before = await self._count_relationships()
        versions_before = self._count_version_files()

        # Execute migration
        start_time = time.time()

        try:
            logger.info(f"Executing migration {migration.full_name}...")

            # Execute the migrate() function
            await migrate_func(context)

            # Calculate execution time
            end_time = time.time()
            result.duration_seconds = end_time - start_time

            # Track statistics after execution
            entities_after = await self._count_entities()
            relationships_after = await self._count_relationships()
            versions_after = self._count_version_files()

            result.entities_created = entities_after - entities_before
            result.relationships_created = relationships_after - relationships_before
            result.versions_created = versions_after - versions_before

            # Capture logs from context (extend, don't replace)
            result.logs.extend(context.logs)

            # Mark as completed
            result.status = MigrationStatus.COMPLETED

            logger.info(
                f"Migration {migration.full_name} completed successfully in "
                f"{result.duration_seconds:.1f}s "
                f"(created: {result.entities_created} entities, "
                f"{result.relationships_created} relationships)"
            )

            # Capture git diff of changes
            git_diff = self._get_git_diff()

            # Store migration logs
            try:
                await self._store_migration_log(migration, result, git_diff)
                logger.info(f"Migration log stored for {migration.full_name}")
            except Exception as log_error:
                logger.error(f"Failed to store migration log: {log_error}")
                # Mark migration as failed if log storage fails
                result.status = MigrationStatus.FAILED
                result.error = log_error
                result.logs.append(f"ERROR: Failed to store migration log: {log_error}")

        except Exception as e:
            # Calculate execution time even on failure
            end_time = time.time()
            result.duration_seconds = end_time - start_time

            # Capture error details
            result.status = MigrationStatus.FAILED
            result.error = e

            # Capture logs from context (extend, don't replace)
            result.logs.extend(context.logs)

            # Add error traceback to logs
            error_traceback = traceback.format_exc()
            result.logs.append(f"ERROR: {e}")
            result.logs.append(f"Traceback:\n{error_traceback}")

            logger.error(
                f"Migration {migration.full_name} failed after "
                f"{result.duration_seconds:.1f}s: {e}\n{error_traceback}"
            )

        return result

    async def _count_entities(self) -> int:
        """
        Count total number of entities in the database.

        Returns:
            Total entity count
        """
        try:
            # Use database's list method with a high limit to get count
            # This is a simple implementation - could be optimized with a dedicated count method
            entities = await self.db.list_entities(limit=1000000)
            return len(entities)
        except Exception as e:
            logger.warning(f"Failed to count entities: {e}")
            return 0

    async def _count_relationships(self) -> int:
        """
        Count total number of relationships in the database.

        Returns:
            Total relationship count
        """
        try:
            # Use database's list method with a high limit to get count
            # This is a simple implementation - could be optimized with a dedicated count method
            relationships = await self.db.list_relationships(limit=1000000)
            return len(relationships)
        except Exception as e:
            logger.warning(f"Failed to count relationships: {e}")
            return 0

    def _count_version_files(self) -> int:
        """
        Count total number of version files in the database.

        Version files are stored in the version/ directory (note: singular)
        in nested subdirectories with .json extension.

        Returns:
            Total version file count
        """
        try:
            version_dir = self.manager.db_path / "version"
            if not version_dir.exists():
                return 0

            # Count all .json files recursively in version directory (including nested folders)
            version_files = list(version_dir.rglob("*.json"))
            return len(version_files)
        except Exception as e:
            logger.warning(f"Failed to count version files: {e}")
            return 0

    def _get_migration_log_dir(self, migration: Migration) -> Path:
        """
        Get the directory path for storing migration logs.

        Args:
            migration: Migration to get log directory for

        Returns:
            Path to migration log directory
        """
        log_base = self.manager.db_path / "migration-logs"
        return log_base / migration.full_name

    def _check_clean_state(self) -> bool:
        """
        Check if the database directory has a clean git state (no uncommitted changes).

        Returns:
            True if clean (no uncommitted changes), False otherwise
        """
        diff = self._get_git_diff()
        return diff is None or len(diff) == 0

    def _get_git_diff(self) -> Optional[str]:
        """
        Get git diff of changes in the database directory.

        This captures all uncommitted changes in the database directory (nes-db)
        including both modified tracked files and new untracked files.

        The nes-db directory is expected to be a git submodule.

        Returns:
            Git diff as string, or None if no changes or error occurred
        """
        db_path = self.manager.db_path
        db_repo_path = db_path.parent  # nes-db directory

        try:
            # Check if it's a git repository (nes-db should be a submodule)
            git_dir = db_repo_path / ".git"
            if not git_dir.exists():
                logger.warning(
                    f"Database directory is not a git repository: {db_repo_path}. "
                    "Expected nes-db to be a git submodule."
                )
                return None

            diff_parts = []

            # Get diff of tracked files (staged and unstaged changes)
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=db_repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"Git diff failed: {result.stderr}")
                return None

            if result.stdout.strip():
                diff_parts.append(result.stdout.strip())

            # Get diff of untracked files (new files created by migration)
            # Use --no-index to diff against /dev/null for new files
            untracked_result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=db_repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if untracked_result.returncode == 0 and untracked_result.stdout.strip():
                untracked_files = untracked_result.stdout.strip().split("\n")
                logger.info(f"Found {len(untracked_files)} untracked files")

                # Generate diff for each untracked file
                for file_path in untracked_files:
                    file_full_path = db_repo_path / file_path
                    if file_full_path.exists() and file_full_path.is_file():
                        try:
                            # Create a diff showing the file as new
                            with open(file_full_path, "r", encoding="utf-8") as f:
                                content = f.read()

                            # Format as a git diff for a new file
                            file_diff = f"diff --git a/{file_path} b/{file_path}\n"
                            file_diff += "new file mode 100644\n"
                            file_diff += "index 0000000..0000000\n"
                            file_diff += "--- /dev/null\n"
                            file_diff += f"+++ b/{file_path}\n"
                            file_diff += (
                                "@@ -0,0 +1," + str(len(content.splitlines())) + " @@\n"
                            )
                            for line in content.splitlines():
                                file_diff += f"+{line}\n"

                            diff_parts.append(file_diff)
                        except Exception as e:
                            logger.warning(
                                f"Failed to read untracked file {file_path}: {e}"
                            )

            # Combine all diffs
            if not diff_parts:
                logger.info("No uncommitted changes detected in database")
                return None

            combined_diff = "\n".join(diff_parts)
            logger.info(
                f"Captured git diff: {len(combined_diff)} characters ({len(diff_parts)} parts)"
            )
            return combined_diff

        except subprocess.TimeoutExpired:
            logger.error("Git diff timed out after 30 seconds")
            return None
        except Exception as e:
            logger.error(f"Failed to get git diff: {e}")
            return None

    async def _is_migration_logged(self, migration: Migration) -> bool:
        """
        Check if a migration has been logged (i.e., already applied).

        Args:
            migration: Migration to check

        Returns:
            True if migration log exists, False otherwise
        """
        log_dir = self._get_migration_log_dir(migration)
        metadata_file = log_dir / "metadata.json"
        return metadata_file.exists()

    async def _store_migration_log(
        self,
        migration: Migration,
        result: MigrationResult,
        git_diff: Optional[str] = None,
    ) -> None:
        """
        Store migration log with metadata and changes.

        Creates a folder structure:
        {db_path}/migration-logs/{migration-name}/
            metadata.json - Migration metadata, statistics, and changes summary
            changes.diff - Git diff of all changes (if available)
            logs.txt - Execution logs

        Args:
            migration: Migration that was executed
            result: Result of migration execution
            git_diff: Optional git diff of changes made

        Raises:
            IOError: If log storage fails
        """
        import json
        from datetime import datetime

        log_dir = self._get_migration_log_dir(migration)

        # Create log directory
        log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Storing migration log in {log_dir}")

        # Store metadata with changes summary
        metadata = {
            "migration_name": migration.full_name,
            "author": migration.author,
            "date": migration.date.isoformat() if migration.date else None,
            "description": migration.description,
            "executed_at": datetime.now().isoformat(),
            "duration_seconds": result.duration_seconds,
            "status": result.status.value,
            "changes": {
                "entities_created": result.entities_created,
                "relationships_created": result.relationships_created,
                "versions_created": result.versions_created,
                "summary": f"Created {result.entities_created} entities, {result.relationships_created} relationships, and {result.versions_created} versions",
                "has_diff": git_diff is not None and len(git_diff) > 0,
            },
        }

        metadata_file = log_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.debug(f"Stored metadata: {metadata_file}")

        # Store diff as separate file if it exists
        if git_diff:
            diff_file = log_dir / "changes.diff"
            with open(diff_file, "w", encoding="utf-8") as f:
                f.write(git_diff)
            logger.debug(f"Stored diff: {diff_file}")

        # Store execution logs
        logs_file = log_dir / "logs.txt"
        with open(logs_file, "w", encoding="utf-8") as f:
            f.write(f"Migration: {migration.full_name}\n")
            f.write(f"Executed at: {datetime.now().isoformat()}\n")
            f.write(f"Duration: {result.duration_seconds:.1f}s\n")
            f.write(f"\n{'='*80}\n")
            f.write("Execution Logs:\n")
            f.write(f"{'='*80}\n\n")
            for log in result.logs:
                f.write(f"{log}\n")

        logger.debug(f"Stored logs: {logs_file}")
        logger.info(f"Migration log stored successfully for {migration.full_name}")

    async def run_migrations(
        self,
        migrations: List[Migration],
        stop_on_failure: bool = True,
    ) -> List[MigrationResult]:
        """
        Execute multiple migrations in sequential order.

        This method:
        - Executes migrations in the order provided (typically sorted by prefix)
        - Skips already-applied migrations automatically
        - Can stop on first failure or continue based on flag
        - Returns results for all migrations (executed, skipped, or failed)

        Args:
            migrations: List of migrations to execute (in order)
            stop_on_failure: If True, stop on first failure; if False, continue (default: True)

        Returns:
            List of MigrationResult objects, one per migration

        Example:
            >>> runner = MigrationRunner(...)
            >>> migrations = [migration1, migration2, migration3]
            >>> results = await runner.run_migrations(migrations)
            >>> for result in results:
            ...     print(f"{result.migration.full_name}: {result.status}")
        """
        logger.info(f"Running batch of {len(migrations)} migrations")

        results = []

        for i, migration in enumerate(migrations, 1):
            logger.info(
                f"Processing migration {i}/{len(migrations)}: {migration.full_name}"
            )

            # Execute migration
            result = await self.run_migration(migration=migration)

            results.append(result)

            # Log result
            if result.status == MigrationStatus.COMPLETED:
                logger.info(
                    f"✓ Migration {migration.full_name} completed successfully "
                    f"({result.entities_created} entities, "
                    f"{result.relationships_created} relationships)"
                )
            elif result.status == MigrationStatus.SKIPPED:
                logger.info(
                    f"⊘ Migration {migration.full_name} skipped (already applied)"
                )
            elif result.status == MigrationStatus.FAILED:
                logger.error(
                    f"✗ Migration {migration.full_name} failed: {result.error}"
                )

                # Stop on failure if flag is set
                if stop_on_failure:
                    logger.error(
                        f"Stopping batch execution due to failure in "
                        f"{migration.full_name}"
                    )
                    break

        # Summary
        completed = sum(1 for r in results if r.status == MigrationStatus.COMPLETED)
        skipped = sum(1 for r in results if r.status == MigrationStatus.SKIPPED)
        failed = sum(1 for r in results if r.status == MigrationStatus.FAILED)

        logger.info(
            f"Batch execution complete: "
            f"{completed} completed, {skipped} skipped, {failed} failed"
        )

        return results
