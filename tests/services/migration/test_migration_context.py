"""
Tests for the Migration Context.

This module tests the MigrationContext class including file reading helpers,
logging mechanism, and service access.
"""

import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from nes.services.migration import MigrationContext


@pytest.fixture
def temp_migration_dir():
    """Create a temporary migration directory with test data files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        migration_dir = Path(tmpdir)

        # Create test CSV file
        csv_file = migration_dir / "test.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "type", "value"])
            writer.writeheader()
            writer.writerow({"name": "Entity 1", "type": "person", "value": "100"})
            writer.writerow(
                {"name": "Entity 2", "type": "organization", "value": "200"}
            )

        # Create test JSON file
        json_file = migration_dir / "test.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "entities": [
                        {"id": "1", "name": "Test 1"},
                        {"id": "2", "name": "Test 2"},
                    ],
                    "count": 2,
                },
                f,
            )

        yield migration_dir


@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    publication_service = Mock()
    search_service = Mock()
    db = Mock()

    return {
        "publication": publication_service,
        "search": search_service,
        "db": db,
    }


def test_migration_context_initialization(temp_migration_dir, mock_services):
    """Test that MigrationContext initializes correctly."""
    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    assert context.publication == mock_services["publication"]
    assert context.search == mock_services["search"]
    assert context.db == mock_services["db"]
    assert context.migration_dir == temp_migration_dir
    assert context.logs == []


def test_migration_dir_property(temp_migration_dir, mock_services):
    """Test that migration_dir property returns the correct path."""
    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    assert context.migration_dir == temp_migration_dir
    assert isinstance(context.migration_dir, Path)


def test_log_message(temp_migration_dir, mock_services, capsys):
    """Test that log() stores messages and prints to console."""
    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    # Log some messages
    context.log("First message")
    context.log("Second message")
    context.log("Third message")

    # Check logs are stored
    assert len(context.logs) == 3
    assert context.logs[0] == "First message"
    assert context.logs[1] == "Second message"
    assert context.logs[2] == "Third message"

    # Check console output
    captured = capsys.readouterr()
    assert "[Migration] First message" in captured.out
    assert "[Migration] Second message" in captured.out
    assert "[Migration] Third message" in captured.out


def test_logs_property_returns_copy(temp_migration_dir, mock_services):
    """Test that logs property returns a copy, not the original list."""
    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    context.log("Test message")

    # Get logs
    logs1 = context.logs
    logs2 = context.logs

    # Modify one copy
    logs1.append("Modified")

    # Original should be unchanged
    assert len(context.logs) == 1
    assert "Modified" not in context.logs

    # Copies should be independent
    assert logs1 != logs2


def test_read_csv(temp_migration_dir, mock_services):
    """Test reading CSV files."""
    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    data = context.read_csv("test.csv")

    assert len(data) == 2
    assert data[0]["name"] == "Entity 1"
    assert data[0]["type"] == "person"
    assert data[0]["value"] == "100"
    assert data[1]["name"] == "Entity 2"
    assert data[1]["type"] == "organization"
    assert data[1]["value"] == "200"


def test_read_csv_file_not_found(temp_migration_dir, mock_services):
    """Test that read_csv raises FileNotFoundError for missing files."""
    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    with pytest.raises(FileNotFoundError) as exc_info:
        context.read_csv("nonexistent.csv")

    assert "CSV file not found: nonexistent.csv" in str(exc_info.value)


def test_read_json(temp_migration_dir, mock_services):
    """Test reading JSON files."""
    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    data = context.read_json("test.json")

    assert data["count"] == 2
    assert len(data["entities"]) == 2
    assert data["entities"][0]["id"] == "1"
    assert data["entities"][0]["name"] == "Test 1"
    assert data["entities"][1]["id"] == "2"
    assert data["entities"][1]["name"] == "Test 2"


def test_read_json_file_not_found(temp_migration_dir, mock_services):
    """Test that read_json raises FileNotFoundError for missing files."""
    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    with pytest.raises(FileNotFoundError) as exc_info:
        context.read_json("nonexistent.json")

    assert "JSON file not found: nonexistent.json" in str(exc_info.value)


def test_read_json_malformed(temp_migration_dir, mock_services):
    """Test that read_json raises JSONDecodeError for malformed JSON."""
    # Create malformed JSON file
    malformed_file = temp_migration_dir / "malformed.json"
    malformed_file.write_text("{ invalid json }")

    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    with pytest.raises(json.JSONDecodeError):
        context.read_json("malformed.json")


def test_read_excel_without_openpyxl(temp_migration_dir, mock_services, monkeypatch):
    """Test that read_excel raises ImportError when openpyxl is not available."""
    # Create a dummy Excel file so we pass the file existence check
    excel_file = temp_migration_dir / "test.xlsx"
    excel_file.write_text("dummy content")

    # Mock openpyxl import to fail
    import builtins

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "openpyxl":
            raise ImportError("No module named 'openpyxl'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    with pytest.raises(ImportError) as exc_info:
        context.read_excel("test.xlsx")

    assert "openpyxl is required" in str(exc_info.value)


def test_read_excel_file_not_found(temp_migration_dir, mock_services):
    """Test that read_excel raises FileNotFoundError for missing files."""
    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    with pytest.raises(FileNotFoundError) as exc_info:
        context.read_excel("nonexistent.xlsx")

    assert "Excel file not found: nonexistent.xlsx" in str(exc_info.value)


def test_service_access(temp_migration_dir, mock_services):
    """Test that services are accessible through the context."""
    context = MigrationContext(
        publication_service=mock_services["publication"],
        search_service=mock_services["search"],
        db=mock_services["db"],
        migration_dir=temp_migration_dir,
    )

    # Verify services are accessible
    assert context.publication is mock_services["publication"]
    assert context.search is mock_services["search"]
    assert context.db is mock_services["db"]

    # Verify we can call methods on services (they're mocks)
    context.publication.some_method()
    mock_services["publication"].some_method.assert_called_once()
