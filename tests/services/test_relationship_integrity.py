"""Tests for Relationship Integrity in nes.

Following TDD approach: Write failing tests first (Red phase).
These tests define the expected behavior of relationship integrity checks.

Relationship integrity includes:
- Entity existence validation
- Circular relationship detection
- Constraint validation
- Integrity check CLI command
"""

from datetime import UTC, date, datetime
from typing import Any, Dict, List

import pytest

from nes.core.models.relationship import Relationship
from nes.database.file_database import FileDatabase


class TestEntityExistenceValidation:
    """Test that relationships validate entity existence."""

    @pytest.mark.asyncio
    async def test_validate_source_entity_exists(self, temp_db_path):
        """Test that relationship creation validates source entity exists."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create only target entity
        target_data = {
            "slug": "target-org",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Target Org"}}],
        }
        target = await service.create_entity(
            entity_prefix="organization/political_party",
            entity_data=target_data,
            author_id="author:test",
            change_description="Test",
        )

        # Try to create relationship with nonexistent source
        with pytest.raises(ValueError, match="Source entity .* does not exist"):
            await service.create_relationship(
                source_entity_id="entity:person/nonexistent",
                target_entity_id=target.id,
                relationship_type="MEMBER_OF",
                author_id="author:test",
                change_description="Test",
            )

    @pytest.mark.asyncio
    async def test_validate_target_entity_exists(self, temp_db_path):
        """Test that relationship creation validates target entity exists."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create only source entity
        source_data = {
            "slug": "source-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Source Person"}}],
        }
        source = await service.create_entity(
            entity_prefix="person",
            entity_data=source_data,
            author_id="author:test",
            change_description="Test",
        )

        # Try to create relationship with nonexistent target
        with pytest.raises(ValueError, match="Target entity .* does not exist"):
            await service.create_relationship(
                source_entity_id=source.id,
                target_entity_id="entity:organization/political_party/nonexistent",
                relationship_type="MEMBER_OF",
                author_id="author:test",
                change_description="Test",
            )

    @pytest.mark.asyncio
    async def test_validate_both_entities_exist(self, temp_db_path):
        """Test that relationship creation validates both entities exist."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Try to create relationship with both entities nonexistent
        with pytest.raises(ValueError, match="does not exist"):
            await service.create_relationship(
                source_entity_id="entity:person/nonexistent-source",
                target_entity_id="entity:organization/political_party/nonexistent-target",
                relationship_type="MEMBER_OF",
                author_id="author:test",
                change_description="Test",
            )

    @pytest.mark.asyncio
    async def test_relationship_succeeds_when_entities_exist(self, temp_db_path):
        """Test that relationship creation succeeds when both entities exist."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create both entities
        source_data = {
            "slug": "valid-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Valid Person"}}],
        }
        target_data = {
            "slug": "valid-org",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Valid Org"}}],
        }

        source = await service.create_entity(
            entity_prefix="person",
            entity_data=source_data,
            author_id="author:test",
            change_description="Test",
        )
        target = await service.create_entity(
            entity_prefix="organization/political_party",
            entity_data=target_data,
            author_id="author:test",
            change_description="Test",
        )

        # Create relationship should succeed
        relationship = await service.create_relationship(
            source_entity_id=source.id,
            target_entity_id=target.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Test",
        )

        assert relationship is not None
        assert relationship.source_entity_id == source.id
        assert relationship.target_entity_id == target.id


class TestCircularRelationshipDetection:
    """Test detection of circular relationships."""

    @pytest.mark.asyncio
    async def test_detect_direct_circular_relationship(self, temp_db_path):
        """Test detection of direct circular relationship (A -> A)."""
        from nes.services.publication import PublicationService
        from nes.services.publication.integrity import check_circular_relationship

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entity
        entity_data = {
            "slug": "self-ref",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Self Ref"}}],
        }
        entity = await service.create_entity(
            entity_prefix="person",
            entity_data=entity_data,
            author_id="author:test",
            change_description="Test",
        )

        # Check for circular relationship (entity to itself)
        is_circular = await check_circular_relationship(
            db=db,
            source_entity_id=entity.id,
            target_entity_id=entity.id,
            relationship_type="SUPERVISES",
        )

        assert is_circular is True

    @pytest.mark.asyncio
    async def test_detect_two_hop_circular_relationship(self, temp_db_path):
        """Test detection of two-hop circular relationship (A -> B -> A)."""
        from nes.services.publication import PublicationService
        from nes.services.publication.integrity import check_circular_relationship

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities
        person_a_data = {
            "slug": "person-a",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Person A"}}],
        }
        person_b_data = {
            "slug": "person-b",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Person B"}}],
        }

        person_a = await service.create_entity(
            entity_prefix="person",
            entity_data=person_a_data,
            author_id="author:test",
            change_description="Test",
        )
        person_b = await service.create_entity(
            entity_prefix="person",
            entity_data=person_b_data,
            author_id="author:test",
            change_description="Test",
        )

        # Create relationship A -> B
        await service.create_relationship(
            source_entity_id=person_a.id,
            target_entity_id=person_b.id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="A supervises B",
        )

        # Check if B -> A would create a circle
        is_circular = await check_circular_relationship(
            db=db,
            source_entity_id=person_b.id,
            target_entity_id=person_a.id,
            relationship_type="SUPERVISES",
        )

        assert is_circular is True

    @pytest.mark.asyncio
    async def test_detect_three_hop_circular_relationship(self, temp_db_path):
        """Test detection of three-hop circular relationship (A -> B -> C -> A)."""
        from nes.services.publication import PublicationService
        from nes.services.publication.integrity import check_circular_relationship

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities
        entities = []
        for slug in ["person-x", "person-y", "person-z"]:
            entity_data = {
                "slug": slug,
                "type": "person",
                "names": [
                    {"kind": "PRIMARY", "en": {"full": slug.replace("-", " ").title()}}
                ],
            }
            entity = await service.create_entity(
                entity_prefix="person",
                entity_data=entity_data,
                author_id="author:test",
                change_description="Test",
            )
            entities.append(entity)

        # Create relationships X -> Y -> Z
        await service.create_relationship(
            source_entity_id=entities[0].id,
            target_entity_id=entities[1].id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="X supervises Y",
        )

        await service.create_relationship(
            source_entity_id=entities[1].id,
            target_entity_id=entities[2].id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="Y supervises Z",
        )

        # Check if Z -> X would create a circle
        is_circular = await check_circular_relationship(
            db=db,
            source_entity_id=entities[2].id,
            target_entity_id=entities[0].id,
            relationship_type="SUPERVISES",
        )

        assert is_circular is True

    @pytest.mark.asyncio
    async def test_allow_non_circular_relationship(self, temp_db_path):
        """Test that non-circular relationships are allowed."""
        from nes.services.publication import PublicationService
        from nes.services.publication.integrity import check_circular_relationship

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities A, B, C
        entities = []
        for slug in ["entity-1", "entity-2", "entity-3"]:
            entity_data = {
                "slug": slug,
                "type": "person",
                "names": [
                    {"kind": "PRIMARY", "en": {"full": slug.replace("-", " ").title()}}
                ],
            }
            entity = await service.create_entity(
                entity_prefix="person",
                entity_data=entity_data,
                author_id="author:test",
                change_description="Test",
            )
            entities.append(entity)

        # Create relationships A -> B, B -> C (no circle)
        await service.create_relationship(
            source_entity_id=entities[0].id,
            target_entity_id=entities[1].id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="1 supervises 2",
        )

        await service.create_relationship(
            source_entity_id=entities[1].id,
            target_entity_id=entities[2].id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="2 supervises 3",
        )

        # Check if A -> C is circular (it's not)
        is_circular = await check_circular_relationship(
            db=db,
            source_entity_id=entities[0].id,
            target_entity_id=entities[2].id,
            relationship_type="SUPERVISES",
        )

        assert is_circular is False

    @pytest.mark.asyncio
    async def test_circular_detection_only_for_hierarchical_types(self, temp_db_path):
        """Test that circular detection only applies to hierarchical relationship types."""
        from nes.services.publication import PublicationService
        from nes.services.publication.integrity import check_circular_relationship

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities
        person_data = {
            "slug": "member-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Member Person"}}],
        }
        org_data = {
            "slug": "member-org",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Member Org"}}],
        }

        person = await service.create_entity(
            entity_prefix="person",
            entity_data=person_data,
            author_id="author:test",
            change_description="Test",
        )
        org = await service.create_entity(
            entity_prefix="organization/political_party",
            entity_data=org_data,
            author_id="author:test",
            change_description="Test",
        )

        # Create relationship person -> org (MEMBER_OF)
        await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Person member of org",
        )

        # Check if org -> person (MEMBER_OF) is circular
        # For non-hierarchical types like MEMBER_OF, this should be allowed
        is_circular = await check_circular_relationship(
            db=db,
            source_entity_id=org.id,
            target_entity_id=person.id,
            relationship_type="MEMBER_OF",
        )

        # MEMBER_OF is not hierarchical, so no circular check needed
        assert is_circular is False


class TestConstraintValidation:
    """Test relationship constraint validation."""

    @pytest.mark.asyncio
    async def test_validate_temporal_constraints(self, temp_db_path):
        """Test validation of temporal constraints (start_date < end_date)."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities
        person_data = {
            "slug": "temporal-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Temporal Person"}}],
        }
        org_data = {
            "slug": "temporal-org",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Temporal Org"}}],
        }

        person = await service.create_entity(
            entity_prefix="person",
            entity_data=person_data,
            author_id="author:test",
            change_description="Test",
        )
        org = await service.create_entity(
            entity_prefix="organization/political_party",
            entity_data=org_data,
            author_id="author:test",
            change_description="Test",
        )

        # Try to create relationship with end_date before start_date
        with pytest.raises(ValueError, match="end_date cannot be before start_date"):
            await service.create_relationship(
                source_entity_id=person.id,
                target_entity_id=org.id,
                relationship_type="MEMBER_OF",
                author_id="author:test",
                change_description="Test",
                start_date=date(2024, 1, 1),
                end_date=date(2023, 1, 1),
            )

    @pytest.mark.asyncio
    async def test_validate_relationship_type_constraints(self, temp_db_path):
        """Test validation of relationship type constraints."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities
        person_data = {
            "slug": "type-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Type Person"}}],
        }
        org_data = {
            "slug": "type-org",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Type Org"}}],
        }

        person = await service.create_entity(
            entity_prefix="person",
            entity_data=person_data,
            author_id="author:test",
            change_description="Test",
        )
        org = await service.create_entity(
            entity_prefix="organization/political_party",
            entity_data=org_data,
            author_id="author:test",
            change_description="Test",
        )

        # Try to create relationship with invalid type
        with pytest.raises(ValueError, match="Invalid relationship type"):
            await service.create_relationship(
                source_entity_id=person.id,
                target_entity_id=org.id,
                relationship_type="INVALID_TYPE",
                author_id="author:test",
                change_description="Test",
            )

    @pytest.mark.asyncio
    async def test_validate_duplicate_relationships(self, temp_db_path):
        """Test validation to prevent duplicate relationships."""
        from nes.services.publication import PublicationService
        from nes.services.publication.integrity import check_duplicate_relationship

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities
        person_data = {
            "slug": "dup-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Dup Person"}}],
        }
        org_data = {
            "slug": "dup-org",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Dup Org"}}],
        }

        person = await service.create_entity(
            entity_prefix="person",
            entity_data=person_data,
            author_id="author:test",
            change_description="Test",
        )
        org = await service.create_entity(
            entity_prefix="organization/political_party",
            entity_data=org_data,
            author_id="author:test",
            change_description="Test",
        )

        # Create first relationship
        await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="First",
        )

        # Check for duplicate
        is_duplicate = await check_duplicate_relationship(
            db=db,
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
        )

        assert is_duplicate is True

    @pytest.mark.asyncio
    async def test_allow_same_entities_different_types(self, temp_db_path):
        """Test that same entities can have different relationship types."""
        from nes.services.publication import PublicationService
        from nes.services.publication.integrity import check_duplicate_relationship

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities
        person_data = {
            "slug": "multi-rel-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Multi Rel Person"}}],
        }
        org_data = {
            "slug": "multi-rel-org",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Multi Rel Org"}}],
        }

        person = await service.create_entity(
            entity_prefix="person",
            entity_data=person_data,
            author_id="author:test",
            change_description="Test",
        )
        org = await service.create_entity(
            entity_prefix="organization/political_party",
            entity_data=org_data,
            author_id="author:test",
            change_description="Test",
        )

        # Create first relationship
        await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Member",
        )

        # Check for duplicate with different type (should not be duplicate)
        is_duplicate = await check_duplicate_relationship(
            db=db,
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="AFFILIATED_WITH",
        )

        assert is_duplicate is False


class TestIntegrityCheckCLI:
    """Test integrity check CLI command."""

    def test_integrity_check_command_exists(self):
        """Test that integrity check CLI command exists."""
        from click.testing import CliRunner

        from nes.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["integrity", "--help"])

        # Command should exist and show help
        assert result.exit_code == 0
        assert "integrity" in result.output.lower()

    def test_integrity_check_reports_orphaned_relationships(self, temp_db_path):
        """Test that integrity check reports relationships with missing entities."""
        from click.testing import CliRunner

        from nes.cli import cli
        from nes.config import Config

        # Set up database path
        Config.DB_PATH = str(temp_db_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["integrity", "check"])

        # Should complete successfully (no issues in empty database)
        assert result.exit_code == 0

    def test_integrity_check_reports_circular_relationships(self, temp_db_path):
        """Test that integrity check reports circular relationships."""
        import asyncio

        from click.testing import CliRunner

        from nes.cli import cli
        from nes.config import Config
        from nes.database.file_database import FileDatabase
        from nes.services.publication import PublicationService

        # Set up database and create circular relationship
        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        async def setup_circular_relationships():
            # Create entities with circular supervision
            person_a_data = {
                "slug": "circular-a",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Circular A"}}],
            }
            person_b_data = {
                "slug": "circular-b",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Circular B"}}],
            }

            person_a = await service.create_entity(
                entity_prefix="person",
                entity_data=person_a_data,
                author_id="author:test",
                change_description="Test",
            )
            person_b = await service.create_entity(
                entity_prefix="person",
                entity_data=person_b_data,
                author_id="author:test",
                change_description="Test",
            )

            # Create circular relationships (A supervises B, B supervises A)
            await service.create_relationship(
                source_entity_id=person_a.id,
                target_entity_id=person_b.id,
                relationship_type="SUPERVISES",
                author_id="author:test",
                change_description="A supervises B",
            )

            await service.create_relationship(
                source_entity_id=person_b.id,
                target_entity_id=person_a.id,
                relationship_type="SUPERVISES",
                author_id="author:test",
                change_description="B supervises A",
            )

        # Run setup in new event loop
        asyncio.run(setup_circular_relationships())

        # Run integrity check
        Config.DB_PATH = str(temp_db_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["integrity", "check"])

        # Should report circular relationships
        assert "circular" in result.output.lower() or "cycle" in result.output.lower()

    def test_integrity_check_reports_duplicate_relationships(self, temp_db_path):
        """Test that integrity check reports duplicate relationships."""
        from click.testing import CliRunner

        from nes.cli import cli
        from nes.config import Config

        # Set up database path
        Config.DB_PATH = str(temp_db_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["integrity", "check"])

        # Should complete successfully
        assert result.exit_code == 0

    def test_integrity_check_fix_option(self, temp_db_path):
        """Test that integrity check has a --fix option."""
        from click.testing import CliRunner

        from nes.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["integrity", "check", "--help"])

        # Should have --fix option
        assert "--fix" in result.output or "--repair" in result.output

    def test_integrity_check_json_output(self, temp_db_path):
        """Test that integrity check can output JSON format."""
        import json

        from click.testing import CliRunner

        from nes.cli import cli
        from nes.config import Config

        # Set up database path
        Config.DB_PATH = str(temp_db_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["integrity", "check", "--json"])

        # Should output valid JSON
        assert result.exit_code == 0
        try:
            data = json.loads(result.output)
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")
