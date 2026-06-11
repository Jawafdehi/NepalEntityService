"""
CLI commands for managing database migrations.

This module provides commands for:
- Creating new migration folders from templates
- Listing all migrations with their status (including pending)
- Running migrations and storing execution logs
"""

import asyncio
from pathlib import Path
from typing import Optional

import click

from nes.config import Config
from nes.services.migration import MigrationManager, MigrationRunner, MigrationStatus


@click.group()
def migration():
    """Manage database migrations.

    Migrations are versioned folders containing Python scripts that apply
    data changes to the entity database. This command group provides tools
    for creating, listing, and running migrations.
    """
    pass


@migration.command()
@click.option(
    "--pending",
    is_flag=True,
    help="Show only pending migrations",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output in JSON format",
)
@click.option(
    "--migrations-dir",
    default="migrations",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to migrations directory",
)
def list(pending: bool, output_json: bool, migrations_dir: str):
    """List migrations with their status.

    Shows all discovered migrations in the migrations/ directory along with
    their metadata (author, date, description) and whether they have been
    applied or are still pending.

    Use --pending flag to show only migrations that haven't been applied yet.
    Use --json flag to output in JSON format.

    Examples:
        nes migration list
        nes migration list --pending
        nes migration list --json
        nes migration list --pending --json
    """

    async def do_list():
        import json

        # Get database path from config
        db_path = Config.get_db_path()

        # Initialize migration manager
        manager = MigrationManager(migrations_dir=Path(migrations_dir), db_path=db_path)

        # Get migrations based on filter
        if pending:
            migrations = await manager.get_pending_migrations()

            if not migrations:
                if output_json:
                    click.echo(
                        json.dumps({"migrations": [], "summary": {"pending": 0}})
                    )
                else:
                    click.echo(
                        "\n✓ No pending migrations. All migrations have been applied.\n"
                    )
                return
        else:
            # Discover all migrations
            migrations = await manager.discover_migrations()

            if not migrations:
                if output_json:
                    click.echo(
                        json.dumps(
                            {
                                "migrations": [],
                                "summary": {"total": 0, "applied": 0, "pending": 0},
                            }
                        )
                    )
                else:
                    click.echo("No migrations found.")
                return

        # Get applied migrations for status
        applied = await manager.get_applied_migrations()

        # Output in JSON format
        if output_json:
            migrations_data = []
            for migration in migrations:
                is_applied = migration.full_name in applied
                migrations_data.append(
                    {
                        "name": migration.full_name,
                        "prefix": migration.prefix,
                        "status": "applied" if is_applied else "pending",
                        "author": migration.author,
                        "date": (
                            migration.date.strftime("%Y-%m-%d")
                            if migration.date
                            else None
                        ),
                        "description": migration.description,
                    }
                )

            # Build summary
            if pending:
                summary = {"pending": len(migrations)}
            else:
                applied_count = len([m for m in migrations if m.full_name in applied])
                summary = {
                    "total": len(migrations),
                    "applied": applied_count,
                    "pending": len(migrations) - applied_count,
                }

            output = {
                "migrations": migrations_data,
                "summary": summary,
            }

            click.echo(json.dumps(output, indent=2))
            return

        # Display migrations in table format
        click.echo(f"\n{'='*80}")
        click.echo(f"{'Migration':<30} {'Status':<12} {'Author':<20} {'Date':<12}")
        click.echo(f"{'='*80}")

        for migration in migrations:
            # Determine status
            is_applied = migration.full_name in applied
            status = "✓ Applied" if is_applied else "○ Pending"

            # Format fields
            name = migration.full_name
            author = migration.author or "Unknown"
            date = migration.date.strftime("%Y-%m-%d") if migration.date else "Unknown"

            # Truncate long fields
            if len(name) > 28:
                name = name[:25] + "..."
            if len(author) > 18:
                author = author[:15] + "..."

            click.echo(f"{name:<30} {status:<12} {author:<20} {date:<12}")

            # Show description if available
            if migration.description:
                desc = migration.description
                if len(desc) > 76:
                    desc = desc[:73] + "..."
                click.echo(f"  {desc}")

        click.echo(f"{'='*80}")

        # Summary
        if pending:
            click.echo(f"\nPending: {len(migrations)} migration(s)")
            click.echo(
                f"\nRun 'nes migration run --all' to execute all pending migrations."
            )
        else:
            total = len(migrations)
            applied_count = len([m for m in migrations if m.full_name in applied])
            pending_count = total - applied_count
            click.echo(
                f"\nTotal: {total} migrations ({applied_count} applied, {pending_count} pending)"
            )

        click.echo()

    # Run async function
    asyncio.run(do_list())


@migration.command()
@click.argument("migration_name", required=False)
@click.option("--all", "run_all", is_flag=True, help="Run all pending migrations")
@click.option(
    "--migrations-dir",
    default="migrations",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to migrations directory",
)
def run(
    migration_name: Optional[str],
    run_all: bool,
    migrations_dir: str,
):
    """Run one or more migrations.

    Execute a specific migration by name, or run all pending migrations
    with the --all flag. Migrations that have already been applied will
    be skipped automatically.

    Examples:
        nes migration run 000-initial-locations
        nes migration run --all
    """
    # Validate arguments
    if not migration_name and not run_all:
        click.echo(
            "Error: Must specify either a migration name or use --all flag.\n"
            "Examples:\n"
            "  nes migration run 000-initial-locations\n"
            "  nes migration run --all",
            err=True,
        )
        raise click.Abort()

    if migration_name and run_all:
        click.echo(
            "Error: Cannot specify both a migration name and --all flag.", err=True
        )
        raise click.Abort()

    async def do_run():
        # Get database path from config
        db_path = Config.get_db_path()

        # Initialize database and services
        click.echo("Initializing database and services...")
        Config.initialize_database(base_path=str(db_path))
        db = Config.get_database()
        publication_service = Config.get_publication_service()
        search_service = Config.get_search_service()

        # Initialize migration manager and runner
        manager = MigrationManager(migrations_dir=Path(migrations_dir), db_path=db_path)

        runner = MigrationRunner(
            publication_service=publication_service,
            search_service=search_service,
            db=db,
            migration_manager=manager,
        )

        # Determine which migrations to run
        if run_all:
            migrations = await manager.get_pending_migrations()

            if not migrations:
                click.echo("\n✓ No pending migrations to run.\n")
                return

            click.echo(f"\nFound {len(migrations)} pending migration(s):\n")
            for migration in migrations:
                click.echo(f"  - {migration.full_name}")
            click.echo()

            # Confirm before running
            click.confirm(
                "Do you want to proceed with running these migrations?", abort=True
            )

            # Run all migrations
            click.echo("\nExecuting migrations...\n")
            results = await runner.run_migrations(
                migrations=migrations,
                stop_on_failure=True,
            )

            # Display results
            click.echo(f"\n{'='*80}")
            click.echo("Migration Results")
            click.echo(f"{'='*80}\n")

            for result in results:
                if result.status == MigrationStatus.COMPLETED:
                    click.echo(f"✓ {result.migration.full_name}")
                    click.echo(f"  Duration: {result.duration_seconds:.1f}s")
                    click.echo(f"  Entities created: {result.entities_created}")
                    click.echo(
                        f"  Relationships created: {result.relationships_created}"
                    )
                    click.echo(f"  Versions created: {result.versions_created}")
                elif result.status == MigrationStatus.SKIPPED:
                    click.echo(
                        f"⊘ {result.migration.full_name} (skipped - already applied)"
                    )
                elif result.status == MigrationStatus.FAILED:
                    click.echo(f"✗ {result.migration.full_name} (FAILED)")
                    click.echo(f"  Error: {result.error}")

                click.echo()

            # Summary
            completed = sum(1 for r in results if r.status == MigrationStatus.COMPLETED)
            skipped = sum(1 for r in results if r.status == MigrationStatus.SKIPPED)
            failed = sum(1 for r in results if r.status == MigrationStatus.FAILED)

            click.echo(f"{'='*80}")
            click.echo(
                f"Summary: {completed} completed, {skipped} skipped, {failed} failed"
            )
            click.echo(f"{'='*80}\n")

            # Exit with error if any failed
            if failed > 0:
                raise click.Abort()

        else:
            # Run single migration
            migration = await manager.get_migration_by_name(migration_name)

            if not migration:
                click.echo(f"Error: Migration '{migration_name}' not found.", err=True)
                raise click.Abort()

            # Check if already applied
            is_applied = await manager.is_migration_applied(migration)

            if is_applied:
                click.echo(
                    f"\nMigration '{migration_name}' has already been applied.\n"
                )
                return

            click.echo(f"\nRunning migration '{migration_name}'...\n")

            # Run migration
            result = await runner.run_migration(migration=migration)

            # Display result
            click.echo(f"\n{'='*80}")

            if result.status == MigrationStatus.COMPLETED:
                click.echo(f"✓ Migration completed successfully")
                click.echo(f"\nDuration: {result.duration_seconds:.1f}s")
                click.echo(f"Entities created: {result.entities_created}")
                click.echo(f"Relationships created: {result.relationships_created}")
                click.echo(f"Versions created: {result.versions_created}")

                if result.logs:
                    click.echo(f"\nLogs:")
                    for log in result.logs:
                        click.echo(f"  {log}")

            elif result.status == MigrationStatus.SKIPPED:
                click.echo(f"⊘ Migration skipped (already applied)")

            elif result.status == MigrationStatus.FAILED:
                click.echo(f"✗ Migration FAILED")
                click.echo(f"\nError: {result.error}")

                if result.logs:
                    click.echo(f"\nLogs:")
                    for log in result.logs:
                        click.echo(f"  {log}")

                click.echo(f"\n{'='*80}\n")
                raise click.Abort()

            click.echo(f"{'='*80}\n")

    # Run async function
    asyncio.run(do_run())


@migration.command()
@click.argument("name")
@click.option(
    "--migrations-dir",
    default="migrations",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Path to migrations directory",
)
@click.option("--author", prompt="Author name", help="Author name address")
def create(name: str, migrations_dir: str, author: str):
    """Create a new migration folder from template.

    Generates a new migration folder with the next available prefix number
    and the specified descriptive name. The folder will contain template
    files for the migration script and README.

    Examples:
        nes migration create add-ministers
        nes migration create update-locations --author user@example.com
    """

    async def do_create():
        from datetime import datetime

        migrations_path = Path(migrations_dir)

        # Create migrations directory if it doesn't exist
        migrations_path.mkdir(parents=True, exist_ok=True)

        # Get database path from config
        db_path = Config.get_db_path()

        # Initialize migration manager to discover existing migrations
        manager = MigrationManager(
            migrations_dir=migrations_path,
            db_path=db_path,
        )

        # Discover existing migrations to determine next prefix
        existing_migrations = await manager.discover_migrations()

        if existing_migrations:
            next_prefix = max(m.prefix for m in existing_migrations) + 1
        else:
            next_prefix = 0

        # Format migration name
        migration_name = f"{next_prefix:03d}-{name}"
        migration_folder = migrations_path / migration_name

        # Check if folder already exists
        if migration_folder.exists():
            click.echo(
                f"Error: Migration folder '{migration_name}' already exists.", err=True
            )
            raise click.Abort()

        # Create migration folder
        click.echo(f"\nCreating migration: {migration_name}")
        migration_folder.mkdir(parents=True)

        # Get current date
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Load template file
        template_path = (
            Path(__file__).parent.parent
            / "services"
            / "migration"
            / "templates"
            / "migrate.py.template"
        )

        if not template_path.exists():
            click.echo(f"Error: Template file not found: {template_path}", err=True)
            raise click.Abort()

        with open(template_path, "r", encoding="utf-8") as f:
            migrate_template = f.read()

        # Replace template variables
        migrate_template = migrate_template.replace("{prefix}", f"{next_prefix:03d}")
        migrate_template = migrate_template.replace("{name}", name)
        migrate_template = migrate_template.replace("{date}", current_date)
        migrate_template = migrate_template.replace("[TODO: Your name]", author)

        migrate_path = migration_folder / "migrate.py"
        with open(migrate_path, "w", encoding="utf-8") as f:
            f.write(migrate_template)

        click.echo(f"  Created: {migrate_path.relative_to(migrations_path.parent)}")

        # Load README template
        readme_template_path = (
            Path(__file__).parent.parent
            / "services"
            / "migration"
            / "templates"
            / "README.md.template"
        )

        if not readme_template_path.exists():
            click.echo(
                f"Error: README template file not found: {readme_template_path}",
                err=True,
            )
            raise click.Abort()

        with open(readme_template_path, "r", encoding="utf-8") as f:
            readme_template = f.read()

        # Replace template variables
        readme_template = readme_template.replace("{prefix}", f"{next_prefix:03d}")
        readme_template = readme_template.replace("{name}", name)

        readme_path = migration_folder / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_template)

        click.echo(f"  Created: {readme_path.relative_to(migrations_path.parent)}")

        # Success message
        click.echo(f"\n✓ Migration folder created successfully!")
        click.echo(f"\nNext steps:")
        click.echo(
            f"  1. Edit {migrate_path.relative_to(migrations_path.parent)} to implement your migration logic"
        )
        click.echo(
            f"  2. Update {readme_path.relative_to(migrations_path.parent)} with migration details"
        )
        click.echo(
            f"  3. Add any data files (CSV, JSON, Excel) to the migration folder"
        )
        click.echo(f"  4. Run your migration with: nes migration run {migration_name}")
        click.echo()

    # Run async function
    asyncio.run(do_create())
