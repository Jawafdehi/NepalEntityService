"""Tests for CLI commands.

Following TDD approach - these tests define the expected CLI behavior.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_database():
    """Create a mock database for testing."""
    mock_db = Mock()
    return mock_db


@pytest.fixture
def mock_search_service():
    """Create a mock search service for testing."""
    mock_service = Mock()
    return mock_service


@pytest.fixture
def mock_publication_service():
    """Create a mock publication service for testing."""
    mock_service = Mock()
    return mock_service


class TestCLIFoundation:
    """Test CLI foundation and basic structure."""

    def test_cli_main_command_exists(self, runner):
        """Test that main CLI command exists and shows help."""
        from nes.cli import cli

        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Nepal Entity Service" in result.output or "nes" in result.output

    def test_cli_has_command_groups(self, runner):
        """Test that CLI has expected command groups."""
        from nes.cli import cli

        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        # Check for command groups
        assert "server" in result.output or "Commands" in result.output


class TestServerCommands:
    """Test server command group."""

    def test_server_start_command_exists(self, runner):
        """Test that 'server start' command exists."""
        from nes.cli import cli

        result = runner.invoke(cli, ["server", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output

    def test_server_dev_command_exists(self, runner):
        """Test that 'server dev' command exists."""
        from nes.cli import cli

        result = runner.invoke(cli, ["server", "--help"])
        assert result.exit_code == 0
        assert "dev" in result.output

    @patch("uvicorn.run")
    def test_server_start_runs_production_server(self, mock_uvicorn_run, runner):
        """Test that 'server start' runs production server."""
        from nes.cli import cli

        result = runner.invoke(cli, ["server", "start"])

        # Should call uvicorn.run
        assert mock_uvicorn_run.called

    @patch("uvicorn.run")
    def test_server_dev_runs_with_reload(self, mock_uvicorn_run, runner):
        """Test that 'server dev' runs with reload enabled."""
        from nes.cli import cli

        result = runner.invoke(cli, ["server", "dev"])

        # Should call uvicorn.run with reload=True
        assert mock_uvicorn_run.called
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs.get("reload") is True

    @patch("uvicorn.run")
    def test_server_start_accepts_host_option(self, mock_uvicorn_run, runner):
        """Test that 'server start' accepts --host option."""
        from nes.cli import cli

        result = runner.invoke(cli, ["server", "start", "--host", "0.0.0.0"])

        assert mock_uvicorn_run.called
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs.get("host") == "0.0.0.0"

    @patch("uvicorn.run")
    def test_server_start_accepts_port_option(self, mock_uvicorn_run, runner):
        """Test that 'server start' accepts --port option."""
        from nes.cli import cli

        result = runner.invoke(cli, ["server", "start", "--port", "9000"])

        assert mock_uvicorn_run.called
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs.get("port") == 9000


class TestSearchCommands:
    """Test search command group."""

    def test_search_command_group_exists(self, runner):
        """Test that 'search' command group exists."""
        from nes.cli import cli

        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0

    @patch("nes.config.Config.get_search_service")
    @patch("nes.config.Config.initialize_database")
    def test_search_entities_command(
        self, mock_init_db, mock_get_service, runner, mock_search_service
    ):
        """Test 'search entities' command with query."""
        from datetime import UTC, datetime

        from nes.cli import cli
        from nes.core.models.base import Name, NameKind, NameParts
        from nes.core.models.person import Person
        from nes.core.models.version import Author, VersionSummary, VersionType

        # Mock search results
        mock_entity = Person(
            slug="ram-chandra-poudel",
            names=[
                Name(kind=NameKind.PRIMARY, en=NameParts(full="Ram Chandra Poudel"))
            ],
            created_at=datetime.now(UTC),
            version_summary=VersionSummary(
                entity_or_relationship_id="entity:person/ram-chandra-poudel",
                type=VersionType.ENTITY,
                version_number=1,
                author=Author(slug="system"),
                change_description="Initial version",
                created_at=datetime.now(UTC),
            ),
        )

        # Create async mock
        async def mock_search(*args, **kwargs):
            return [mock_entity]

        mock_search_service.search_entities = mock_search
        mock_get_service.return_value = mock_search_service

        result = runner.invoke(cli, ["search", "entities", "poudel"])

        assert result.exit_code == 0
        assert (
            "ram-chandra-poudel" in result.output
            or "Ram Chandra Poudel" in result.output
        )

    @patch("nes.config.Config.get_search_service")
    @patch("nes.config.Config.initialize_database")
    def test_search_entities_with_type_filter(
        self, mock_init_db, mock_get_service, runner, mock_search_service
    ):
        """Test 'search entities' with --type filter."""
        from nes.cli import cli

        # Create async mock
        async def mock_search(*args, **kwargs):
            # Verify entity_type was passed
            assert kwargs.get("entity_type") == "person"
            return []

        mock_search_service.search_entities = mock_search
        mock_get_service.return_value = mock_search_service

        result = runner.invoke(cli, ["search", "entities", "test", "--type", "person"])

        assert result.exit_code == 0

    @patch("nes.config.Config.get_search_service")
    @patch("nes.config.Config.initialize_database")
    def test_search_entities_with_limit(
        self, mock_init_db, mock_get_service, runner, mock_search_service
    ):
        """Test 'search entities' with --limit option."""
        from nes.cli import cli

        # Create async mock
        async def mock_search(*args, **kwargs):
            # Verify limit was passed
            assert kwargs.get("limit") == 5
            return []

        mock_search_service.search_entities = mock_search
        mock_get_service.return_value = mock_search_service

        result = runner.invoke(cli, ["search", "entities", "test", "--limit", "5"])

        assert result.exit_code == 0

    @patch("nes.config.Config.get_search_service")
    @patch("nes.config.Config.initialize_database")
    def test_search_relationships_command(
        self, mock_init_db, mock_get_service, runner, mock_search_service
    ):
        """Test 'search relationships' command."""
        from nes.cli import cli

        # Create async mock
        async def mock_search(*args, **kwargs):
            return []

        mock_search_service.search_relationships = mock_search
        mock_get_service.return_value = mock_search_service

        result = runner.invoke(cli, ["search", "relationships", "--type", "MEMBER_OF"])

        assert result.exit_code == 0

    @patch("nes.config.Config.get_database")
    @patch("nes.config.Config.initialize_database")
    def test_show_entity_command(
        self, mock_init_db, mock_get_db, runner, mock_database
    ):
        """Test 'show' command to display entity details."""
        from datetime import UTC, datetime

        from nes.cli import cli
        from nes.core.models.base import Name, NameKind, NameParts
        from nes.core.models.person import Person
        from nes.core.models.version import Author, VersionSummary, VersionType

        # Mock entity
        mock_entity = Person(
            slug="ram-chandra-poudel",
            names=[
                Name(kind=NameKind.PRIMARY, en=NameParts(full="Ram Chandra Poudel"))
            ],
            created_at=datetime.now(UTC),
            version_summary=VersionSummary(
                entity_or_relationship_id="entity:person/ram-chandra-poudel",
                type=VersionType.ENTITY,
                version_number=1,
                author=Author(slug="system"),
                change_description="Initial version",
                created_at=datetime.now(UTC),
            ),
        )

        # Create async mock
        async def mock_get_entity(entity_id):
            return mock_entity

        mock_database.get_entity = mock_get_entity
        mock_get_db.return_value = mock_database

        result = runner.invoke(cli, ["show", "entity:person/ram-chandra-poudel"])

        assert result.exit_code == 0
        assert (
            "ram-chandra-poudel" in result.output
            or "Ram Chandra Poudel" in result.output
        )

    @patch("nes.config.Config.get_database")
    @patch("nes.config.Config.initialize_database")
    def test_versions_command(self, mock_init_db, mock_get_db, runner, mock_database):
        """Test 'versions' command to show version history."""
        from nes.cli import cli

        # Create async mock
        async def mock_list_versions(*args, **kwargs):
            return []

        mock_database.list_versions_by_entity = mock_list_versions
        mock_get_db.return_value = mock_database

        result = runner.invoke(cli, ["versions", "entity:person/ram-chandra-poudel"])

        assert result.exit_code == 0


@pytest.mark.skip(reason="Data management commands not yet implemented")
class TestDataManagementCommands:
    """Test data management command group."""

    def test_data_command_group_exists(self, runner):
        """Test that 'data' command group exists."""
        from nes.cli import cli

        result = runner.invoke(cli, ["data", "--help"])
        assert result.exit_code == 0

    @patch("nes.cli.Config.get_publication_service")
    @patch("builtins.open", create=True)
    def test_data_import_command(
        self, mock_open, mock_get_service, runner, mock_publication_service
    ):
        """Test 'data import' command."""
        from nes.cli import cli

        # Mock file content
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(
            [
                {
                    "slug": "test-entity",
                    "type": "person",
                    "names": [{"kind": "PRIMARY", "en": {"full": "Test Entity"}}],
                }
            ]
        )
        mock_open.return_value = mock_file

        mock_publication_service.create_entity = Mock()
        mock_get_service.return_value = mock_publication_service

        result = runner.invoke(cli, ["data", "import", "test.json"])

        # Command should attempt to import
        assert result.exit_code == 0 or "import" in result.output.lower()

    @patch("nes.cli.Config.get_search_service")
    def test_data_export_command(self, mock_get_service, runner, mock_search_service):
        """Test 'data export' command."""
        from nes.cli import cli

        mock_search_service.search_entities = Mock(return_value=[])
        mock_get_service.return_value = mock_search_service

        result = runner.invoke(cli, ["data", "export", "--query", "test"])

        assert result.exit_code == 0 or "export" in result.output.lower()

    @patch("nes.cli.Config.get_database")
    def test_data_validate_command(self, mock_get_db, runner, mock_database):
        """Test 'data validate' command for data quality checks."""
        from nes.cli import cli

        mock_database.list_entities = Mock(return_value=[])
        mock_get_db.return_value = mock_database

        result = runner.invoke(cli, ["data", "validate"])

        assert result.exit_code == 0 or "validate" in result.output.lower()

    @patch("nes.cli.Config.get_database")
    def test_data_stats_command(self, mock_get_db, runner, mock_database):
        """Test 'data stats' command for database statistics."""
        from nes.cli import cli

        mock_database.list_entities = Mock(return_value=[])
        mock_database.list_relationships = Mock(return_value=[])
        mock_get_db.return_value = mock_database

        result = runner.invoke(cli, ["data", "stats"])

        assert result.exit_code == 0 or "stats" in result.output.lower()


@pytest.mark.skip(reason="Analytics commands not yet implemented")
class TestAnalyticsCommands:
    """Test analytics command group."""

    def test_analytics_command_group_exists(self, runner):
        """Test that 'analytics' command group exists."""
        from nes.cli import cli

        result = runner.invoke(cli, ["analytics", "--help"])
        assert result.exit_code == 0

    @patch("nes.cli.Config.get_database")
    def test_analytics_report_command(self, mock_get_db, runner, mock_database):
        """Test 'analytics report' command."""
        from nes.cli import cli

        mock_database.list_entities = Mock(return_value=[])
        mock_database.list_relationships = Mock(return_value=[])
        mock_get_db.return_value = mock_database

        result = runner.invoke(cli, ["analytics", "report"])

        assert result.exit_code == 0 or "report" in result.output.lower()

    @patch("nes.cli.Config.get_database")
    def test_analytics_report_format_option(self, mock_get_db, runner, mock_database):
        """Test 'analytics report' with --format option."""
        from nes.cli import cli

        mock_database.list_entities = Mock(return_value=[])
        mock_database.list_relationships = Mock(return_value=[])
        mock_get_db.return_value = mock_database

        result = runner.invoke(cli, ["analytics", "report", "--format", "json"])

        # Should accept format option
        assert result.exit_code == 0 or "format" in result.output.lower()


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_invalid_command_shows_error(self, runner):
        """Test that invalid command shows helpful error."""
        from nes.cli import cli

        result = runner.invoke(cli, ["invalid-command"])

        assert result.exit_code != 0

    @patch("nes.config.Config.get_database")
    @patch("nes.config.Config.initialize_database")
    def test_show_nonexistent_entity_shows_error(
        self, mock_init_db, mock_get_db, runner, mock_database
    ):
        """Test that showing non-existent entity shows error."""
        from nes.cli import cli

        # Create async mock
        async def mock_get_entity(entity_id):
            return None

        mock_database.get_entity = mock_get_entity
        mock_get_db.return_value = mock_database

        result = runner.invoke(cli, ["show", "entity:person/nonexistent"])

        assert result.exit_code != 0 or "not found" in result.output.lower()


class TestCLIOutputFormatting:
    """Test CLI output formatting."""

    @patch("nes.config.Config.get_search_service")
    @patch("nes.config.Config.initialize_database")
    def test_search_output_is_readable(
        self, mock_init_db, mock_get_service, runner, mock_search_service
    ):
        """Test that search output is human-readable."""
        from datetime import UTC, datetime

        from nes.cli import cli
        from nes.core.models.base import Name, NameKind, NameParts
        from nes.core.models.person import Person
        from nes.core.models.version import Author, VersionSummary, VersionType

        mock_entity = Person(
            slug="test-entity",
            names=[Name(kind=NameKind.PRIMARY, en=NameParts(full="Test Entity"))],
            created_at=datetime.now(UTC),
            version_summary=VersionSummary(
                entity_or_relationship_id="entity:person/test-entity",
                type=VersionType.ENTITY,
                version_number=1,
                author=Author(slug="system"),
                change_description="Initial version",
                created_at=datetime.now(UTC),
            ),
        )

        # Create async mock
        async def mock_search(*args, **kwargs):
            return [mock_entity]

        mock_search_service.search_entities = mock_search
        mock_get_service.return_value = mock_search_service

        result = runner.invoke(cli, ["search", "entities", "test"])

        assert result.exit_code == 0
        # Output should contain entity information
        assert "test" in result.output.lower()

    @patch("nes.config.Config.get_database")
    @patch("nes.config.Config.initialize_database")
    def test_show_output_includes_json_option(
        self, mock_init_db, mock_get_db, runner, mock_database
    ):
        """Test that show command supports --json output format."""
        from datetime import UTC, datetime

        from nes.cli import cli
        from nes.core.models.base import Name, NameKind, NameParts
        from nes.core.models.person import Person
        from nes.core.models.version import Author, VersionSummary, VersionType

        mock_entity = Person(
            slug="test-entity",
            names=[Name(kind=NameKind.PRIMARY, en=NameParts(full="Test Entity"))],
            created_at=datetime.now(UTC),
            version_summary=VersionSummary(
                entity_or_relationship_id="entity:person/test-entity",
                type=VersionType.ENTITY,
                version_number=1,
                author=Author(slug="system"),
                change_description="Initial version",
                created_at=datetime.now(UTC),
            ),
        )

        # Create async mock
        async def mock_get_entity(entity_id):
            return mock_entity

        mock_database.get_entity = mock_get_entity
        mock_get_db.return_value = mock_database

        result = runner.invoke(cli, ["show", "entity:person/test-entity", "--json"])

        # Should output JSON format
        assert result.exit_code == 0
