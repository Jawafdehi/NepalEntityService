"""Tests for Publication Service in nes.

Following TDD approach: Write failing tests first (Red phase).
These tests define the expected behavior of the Publication Service.

The Publication Service is the central orchestration layer that manages:
- Entity lifecycle (creation, updates, retrieval, deletion)
- Relationship management with bidirectional consistency
- Automatic versioning for all changes
- Author attribution tracking
- Coordinated operations across entities and relationships
"""

from datetime import UTC, date, datetime
from typing import Optional

import pytest

from nes.core.models.base import Name, NameKind
from nes.core.models.entity import EntitySubType, EntityType
from nes.core.models.organization import PoliticalParty
from nes.core.models.person import Person
from nes.core.models.relationship import Relationship
from nes.core.models.version import Author, Version, VersionSummary, VersionType
from nes.database.file_database import FileDatabase


class TestPublicationServiceFoundation:
    """Test Publication Service initialization and basic structure."""

    @pytest.mark.asyncio
    async def test_publication_service_initialization(self, temp_db_path):
        """Test that PublicationService can be initialized with a database."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        assert service is not None
        assert service.database == db

    @pytest.mark.asyncio
    async def test_publication_service_requires_database(self):
        """Test that PublicationService requires a database instance."""
        from nes.services.publication import PublicationService

        with pytest.raises(TypeError):
            PublicationService()


class TestPublicationServiceEntityCreation:
    """Test entity creation with automatic versioning."""

    @pytest.mark.asyncio
    async def test_create_entity_with_automatic_versioning(self, temp_db_path):
        """Test creating an entity automatically creates version 1."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entity data
        entity_data = {
            "slug": "ram-chandra-poudel",
            "type": "person",
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {
                        "full": "Ram Chandra Poudel",
                        "given": "Ram Chandra",
                        "family": "Poudel",
                    },
                    "ne": {
                        "full": "राम चन्द्र पौडेल",
                        "given": "राम चन्द्र",
                        "family": "पौडेल",
                    },
                }
            ],
            "attributes": {"party": "nepali-congress"},
        }

        # Create entity
        entity = await service.create_entity(
            entity_type=EntityType.PERSON,
            entity_data=entity_data,
            author_id="author:system-importer",
            change_description="Initial import",
        )

        # Verify entity was created
        assert entity is not None
        assert entity.slug == "ram-chandra-poudel"
        assert entity.type == EntityType.PERSON

        # Verify version was created automatically
        assert entity.version_summary is not None
        assert entity.version_summary.version_number == 1
        assert entity.version_summary.author.id == "author:system-importer"
        assert entity.version_summary.change_description == "Initial import"

    @pytest.mark.asyncio
    async def test_create_entity_stores_in_database(self, temp_db_path):
        """Test that created entity is stored in database."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        entity_data = {
            "slug": "sher-bahadur-deuba",
            "type": "person",
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {"full": "Sher Bahadur Deuba"},
                    "ne": {"full": "शेरबहादुर देउवा"},
                }
            ],
        }

        entity = await service.create_entity(
            entity_type=EntityType.PERSON,
            entity_data=entity_data,
            author_id="author:system-importer",
            change_description="Initial import",
        )

        # Retrieve from database
        retrieved = await db.get_entity(entity.id)
        assert retrieved is not None
        assert retrieved.slug == "sher-bahadur-deuba"

    @pytest.mark.asyncio
    async def test_create_entity_validates_required_fields(self, temp_db_path):
        """Test that entity creation validates required fields."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Missing required 'names' field
        invalid_data = {"slug": "invalid-entity", "type": "person"}

        with pytest.raises(ValueError):
            await service.create_entity(
                entity_type=EntityType.PERSON,
                entity_data=invalid_data,
                author_id="author:system-importer",
                change_description="Test",
            )

    @pytest.mark.asyncio
    async def test_create_entity_requires_primary_name(self, temp_db_path):
        """Test that entity creation requires at least one PRIMARY name."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Names without PRIMARY kind
        invalid_data = {
            "slug": "invalid-entity",
            "type": "person",
            "names": [{"kind": "ALIAS", "en": {"full": "Some Name"}}],
        }

        with pytest.raises(ValueError):
            await service.create_entity(
                entity_type=EntityType.PERSON,
                entity_data=invalid_data,
                author_id="author:system-importer",
                change_description="Test",
            )


class TestPublicationServiceEntityUpdates:
    """Test entity updates with version creation."""

    @pytest.mark.asyncio
    async def test_update_entity_creates_new_version(self, temp_db_path):
        """Test that updating an entity creates a new version."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create initial entity
        entity_data = {
            "slug": "pushpa-kamal-dahal",
            "type": "person",
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {"full": "Pushpa Kamal Dahal"},
                    "ne": {"full": "पुष्पकमल दाहाल"},
                }
            ],
        }

        entity = await service.create_entity(
            entity_type=EntityType.PERSON,
            entity_data=entity_data,
            author_id="author:system-importer",
            change_description="Initial import",
        )

        assert entity.version_summary.version_number == 1

        # Update entity
        entity.attributes = {"party": "cpn-maoist-centre", "alias": "Prachanda"}

        updated_entity = await service.update_entity(
            entity=entity,
            author_id="author:data-maintainer",
            change_description="Added party affiliation",
        )

        # Verify new version was created
        assert updated_entity.version_summary.version_number == 2
        assert (
            updated_entity.version_summary.change_description
            == "Added party affiliation"
        )
        assert updated_entity.attributes["party"] == "cpn-maoist-centre"

    @pytest.mark.asyncio
    async def test_update_entity_preserves_history(self, temp_db_path):
        """Test that entity updates preserve version history."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create and update entity
        entity_data = {
            "slug": "kp-oli",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "KP Sharma Oli"}}],
        }

        entity = await service.create_entity(
            entity_type=EntityType.PERSON,
            entity_data=entity_data,
            author_id="author:system-importer",
            change_description="Initial",
        )

        entity.attributes = {"position": "Prime Minister"}
        await service.update_entity(
            entity=entity, author_id="author:maintainer", change_description="Update 1"
        )

        # Get version history
        versions = await service.get_entity_versions(entity_id=entity.id)

        assert len(versions) >= 2
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2


class TestPublicationServiceEntityRetrieval:
    """Test entity retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_entity_by_id(self, temp_db_path):
        """Test retrieving an entity by its ID."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entity
        entity_data = {
            "slug": "test-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Test Person"}}],
        }

        created = await service.create_entity(
            entity_type=EntityType.PERSON,
            entity_data=entity_data,
            author_id="author:test",
            change_description="Test",
        )

        # Retrieve entity
        retrieved = await service.get_entity(entity_id=created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.slug == "test-person"

    @pytest.mark.asyncio
    async def test_get_entity_returns_none_for_nonexistent(self, temp_db_path):
        """Test that getting a nonexistent entity returns None."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        result = await service.get_entity(entity_id="entity:person/nonexistent")

        assert result is None


class TestPublicationServiceEntityDeletion:
    """Test entity deletion (hard delete)."""

    @pytest.mark.asyncio
    async def test_delete_entity_hard_delete(self, temp_db_path):
        """Test that deleting an entity performs hard delete."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entity
        entity_data = {
            "slug": "to-delete",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "To Delete"}}],
        }

        entity = await service.create_entity(
            entity_type=EntityType.PERSON,
            entity_data=entity_data,
            author_id="author:test",
            change_description="Test",
        )

        # Delete entity
        result = await service.delete_entity(
            entity_id=entity.id,
            author_id="author:test",
            change_description="Deletion test",
        )

        assert result is True

        # Verify entity is completely removed (hard delete)
        deleted_entity = await service.get_entity(entity_id=entity.id)
        assert deleted_entity is None


class TestPublicationServiceRelationshipCreation:
    """Test relationship creation with versioning."""

    @pytest.mark.asyncio
    async def test_create_relationship_with_versioning(self, temp_db_path):
        """Test creating a relationship automatically creates version 1."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities first
        person_data = {
            "slug": "politician-a",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Politician A"}}],
        }
        org_data = {
            "slug": "party-a",
            "type": "organization",
            "sub_type": "political_party",
            "names": [{"kind": "PRIMARY", "en": {"full": "Party A"}}],
        }

        person = await service.create_entity(
            EntityType.PERSON, person_data, "author:test", "Test"
        )
        org = await service.create_entity(
            EntityType.ORGANIZATION,
            org_data,
            "author:test",
            "Test",
            EntitySubType.POLITICAL_PARTY,
        )

        # Create relationship
        relationship = await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Initial relationship",
            start_date=date(2020, 1, 1),
        )

        assert relationship is not None
        assert relationship.source_entity_id == person.id
        assert relationship.target_entity_id == org.id
        assert relationship.type == "MEMBER_OF"
        assert relationship.version_summary.version_number == 1

    @pytest.mark.asyncio
    async def test_create_relationship_validates_entity_existence(self, temp_db_path):
        """Test that relationship creation validates entity existence."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Try to create relationship with nonexistent entities
        with pytest.raises(ValueError):
            await service.create_relationship(
                source_entity_id="entity:person/nonexistent",
                target_entity_id="entity:organization/political_party/nonexistent",
                relationship_type="MEMBER_OF",
                author_id="author:test",
                change_description="Test",
            )


class TestPublicationServiceRelationshipUpdates:
    """Test relationship updates with versioning."""

    @pytest.mark.asyncio
    async def test_update_relationship_creates_new_version(self, temp_db_path):
        """Test that updating a relationship creates a new version."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities and relationship
        person_data = {
            "slug": "pol-b",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Pol B"}}],
        }
        org_data = {
            "slug": "party-b",
            "type": "organization",
            "sub_type": "political_party",
            "names": [{"kind": "PRIMARY", "en": {"full": "Party B"}}],
        }

        person = await service.create_entity(
            EntityType.PERSON, person_data, "author:test", "Test"
        )
        org = await service.create_entity(
            EntityType.ORGANIZATION,
            org_data,
            "author:test",
            "Test",
            EntitySubType.POLITICAL_PARTY,
        )

        relationship = await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Initial",
        )

        # Update relationship
        relationship.end_date = date(2023, 12, 31)

        updated = await service.update_relationship(
            relationship=relationship,
            author_id="author:test",
            change_description="Added end date",
        )

        assert updated.version_summary.version_number == 2
        assert updated.end_date == date(2023, 12, 31)


class TestPublicationServiceRelationshipDeletion:
    """Test relationship deletion."""

    @pytest.mark.asyncio
    async def test_delete_relationship(self, temp_db_path):
        """Test deleting a relationship."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities and relationship
        person_data = {
            "slug": "pol-c",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Pol C"}}],
        }
        org_data = {
            "slug": "party-c",
            "type": "organization",
            "sub_type": "political_party",
            "names": [{"kind": "PRIMARY", "en": {"full": "Party C"}}],
        }

        person = await service.create_entity(
            EntityType.PERSON, person_data, "author:test", "Test"
        )
        org = await service.create_entity(
            EntityType.ORGANIZATION,
            org_data,
            "author:test",
            "Test",
            EntitySubType.POLITICAL_PARTY,
        )

        relationship = await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Test",
        )

        # Delete relationship
        result = await service.delete_relationship(
            relationship_id=relationship.id,
            author_id="author:test",
            change_description="Deletion",
        )

        assert result is True


class TestPublicationServiceBidirectionalConsistency:
    """Test bidirectional relationship consistency."""

    @pytest.mark.asyncio
    async def test_relationship_bidirectional_consistency(self, temp_db_path):
        """Test that relationships maintain bidirectional consistency."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities
        person_data = {
            "slug": "pol-d",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Pol D"}}],
        }
        org_data = {
            "slug": "party-d",
            "type": "organization",
            "sub_type": "political_party",
            "names": [{"kind": "PRIMARY", "en": {"full": "Party D"}}],
        }

        person = await service.create_entity(
            EntityType.PERSON, person_data, "author:test", "Test"
        )
        org = await service.create_entity(
            EntityType.ORGANIZATION,
            org_data,
            "author:test",
            "Test",
            EntitySubType.POLITICAL_PARTY,
        )

        # Create relationship
        relationship = await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Test",
        )

        # Query relationships from both directions
        from_person = await service.get_relationships_by_entity(
            entity_id=person.id, direction="source"
        )

        from_org = await service.get_relationships_by_entity(
            entity_id=org.id, direction="target"
        )

        # Both queries should return the same relationship
        assert len(from_person) == 1
        assert len(from_org) == 1
        assert from_person[0].id == relationship.id
        assert from_org[0].id == relationship.id


class TestPublicationServiceCoordinatedOperations:
    """Test coordinated operations across entities and relationships."""

    @pytest.mark.asyncio
    async def test_update_entity_with_relationships(self, temp_db_path):
        """Test atomic update of entity with its relationships."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities
        person_data = {
            "slug": "pol-e",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Pol E"}}],
        }
        org1_data = {
            "slug": "party-e1",
            "type": "organization",
            "sub_type": "political_party",
            "names": [{"kind": "PRIMARY", "en": {"full": "Party E1"}}],
        }
        org2_data = {
            "slug": "party-e2",
            "type": "organization",
            "sub_type": "political_party",
            "names": [{"kind": "PRIMARY", "en": {"full": "Party E2"}}],
        }

        person = await service.create_entity(
            EntityType.PERSON, person_data, "author:test", "Test"
        )
        org1 = await service.create_entity(
            EntityType.ORGANIZATION,
            org1_data,
            "author:test",
            "Test",
            EntitySubType.POLITICAL_PARTY,
        )
        org2 = await service.create_entity(
            EntityType.ORGANIZATION,
            org2_data,
            "author:test",
            "Test",
            EntitySubType.POLITICAL_PARTY,
        )

        # Create initial relationship
        rel1 = await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org1.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Initial",
        )

        # Update entity and add new relationship atomically
        person.attributes = {"status": "active"}

        new_relationships = [
            {
                "source_entity_id": person.id,
                "target_entity_id": org2.id,
                "relationship_type": "AFFILIATED_WITH",
                "start_date": date(2024, 1, 1),
            }
        ]

        result = await service.update_entity_with_relationships(
            entity=person,
            new_relationships=new_relationships,
            author_id="author:test",
            change_description="Updated with new affiliation",
        )

        assert result["entity"].attributes["status"] == "active"
        assert len(result["relationships"]) == 1

    @pytest.mark.asyncio
    async def test_batch_create_entities(self, temp_db_path):
        """Test batch creation of multiple entities."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        entities_data = [
            {
                "slug": "batch-1",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Batch 1"}}],
            },
            {
                "slug": "batch-2",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Batch 2"}}],
            },
            {
                "slug": "batch-3",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Batch 3"}}],
            },
        ]

        results = await service.batch_create_entities(
            entities_data=entities_data,
            author_id="author:test",
            change_description="Batch import",
        )

        assert len(results) == 3
        assert all(e.version_summary.version_number == 1 for e in results)


class TestPublicationServiceRollback:
    """Test rollback mechanisms for failed operations."""

    @pytest.mark.asyncio
    async def test_rollback_on_validation_failure(self, temp_db_path):
        """Test that failed operations don't leave partial data."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Try to create entity with invalid data
        invalid_data = {
            "slug": "invalid",
            "type": "person",
            "names": [],  # Invalid: no names
        }

        with pytest.raises(ValueError):
            await service.create_entity(
                entity_type=EntityType.PERSON,
                entity_data=invalid_data,
                author_id="author:test",
                change_description="Test",
            )

        # Verify no entity was created
        result = await db.get_entity("entity:person/invalid")
        assert result is None

    @pytest.mark.asyncio
    async def test_rollback_coordinated_operation_failure(self, temp_db_path):
        """Test rollback when coordinated operation fails."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entity
        person_data = {
            "slug": "rollback-test",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Rollback Test"}}],
        }
        person = await service.create_entity(
            EntityType.PERSON, person_data, "author:test", "Test"
        )

        # Try coordinated update with invalid relationship
        person.attributes = {"updated": "yes"}

        invalid_relationships = [
            {
                "source_entity_id": person.id,
                "target_entity_id": "entity:organization/political_party/nonexistent",  # Doesn't exist
                "relationship_type": "MEMBER_OF",
            }
        ]

        with pytest.raises(ValueError):
            await service.update_entity_with_relationships(
                entity=person,
                new_relationships=invalid_relationships,
                author_id="author:test",
                change_description="Should fail",
            )

        # Verify entity wasn't updated
        retrieved = await db.get_entity(person.id)
        assert retrieved.attributes is None or "updated" not in retrieved.attributes


class TestPublicationServiceBusinessRules:
    """Test business rule enforcement."""

    @pytest.mark.asyncio
    async def test_enforce_unique_slug_per_type(self, temp_db_path):
        """Test that slugs must be unique within entity type."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create first entity
        entity_data = {
            "slug": "duplicate-slug",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "First"}}],
        }
        await service.create_entity(
            EntityType.PERSON, entity_data, "author:test", "Test"
        )

        # Try to create second entity with same slug and type
        duplicate_data = {
            "slug": "duplicate-slug",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Second"}}],
        }

        with pytest.raises(ValueError):
            await service.create_entity(
                EntityType.PERSON, duplicate_data, "author:test", "Test"
            )

    @pytest.mark.asyncio
    async def test_enforce_relationship_temporal_consistency(self, temp_db_path):
        """Test that relationship dates are temporally consistent."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities
        person_data = {
            "slug": "temporal-test",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Temporal"}}],
        }
        org_data = {
            "slug": "org-temporal",
            "type": "organization",
            "sub_type": "political_party",
            "names": [{"kind": "PRIMARY", "en": {"full": "Org"}}],
        }

        person = await service.create_entity(
            EntityType.PERSON, person_data, "author:test", "Test"
        )
        org = await service.create_entity(
            EntityType.ORGANIZATION,
            org_data,
            "author:test",
            "Test",
            EntitySubType.POLITICAL_PARTY,
        )

        # Try to create relationship with end_date before start_date
        with pytest.raises(ValueError):
            await service.create_relationship(
                source_entity_id=person.id,
                target_entity_id=org.id,
                relationship_type="MEMBER_OF",
                author_id="author:test",
                change_description="Test",
                start_date=date(2024, 1, 1),
                end_date=date(2023, 1, 1),  # Before start date
            )

    @pytest.mark.asyncio
    async def test_enforce_valid_relationship_types(self, temp_db_path):
        """Test that only valid relationship types are allowed."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities
        person_data = {
            "slug": "rel-type-test",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Test"}}],
        }
        org_data = {
            "slug": "org-rel-type",
            "type": "organization",
            "sub_type": "political_party",
            "names": [{"kind": "PRIMARY", "en": {"full": "Org"}}],
        }

        person = await service.create_entity(
            EntityType.PERSON, person_data, "author:test", "Test"
        )
        org = await service.create_entity(
            EntityType.ORGANIZATION,
            org_data,
            "author:test",
            "Test",
            EntitySubType.POLITICAL_PARTY,
        )

        # Try to create relationship with invalid type
        with pytest.raises(ValueError):
            await service.create_relationship(
                source_entity_id=person.id,
                target_entity_id=org.id,
                relationship_type="INVALID_TYPE",
                author_id="author:test",
                change_description="Test",
            )


class TestPublicationServiceVersionManagement:
    """Test version and author management."""

    @pytest.mark.asyncio
    async def test_get_entity_versions(self, temp_db_path):
        """Test retrieving version history for an entity."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create and update entity multiple times
        entity_data = {
            "slug": "version-test",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Version Test"}}],
        }
        entity = await service.create_entity(
            EntityType.PERSON, entity_data, "author:test", "Initial"
        )

        entity.attributes = {"update": "1"}
        await service.update_entity(entity, "author:test", "Update 1")

        entity.attributes = {"update": "2"}
        await service.update_entity(entity, "author:test", "Update 2")

        # Get versions
        versions = await service.get_entity_versions(entity_id=entity.id)

        assert len(versions) == 3
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2
        assert versions[2].version_number == 3

    @pytest.mark.asyncio
    async def test_get_relationship_versions(self, temp_db_path):
        """Test retrieving version history for a relationship."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities and relationship
        person_data = {
            "slug": "rel-version",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Rel Version"}}],
        }
        org_data = {
            "slug": "org-version",
            "type": "organization",
            "sub_type": "political_party",
            "names": [{"kind": "PRIMARY", "en": {"full": "Org"}}],
        }

        person = await service.create_entity(
            EntityType.PERSON, person_data, "author:test", "Test"
        )
        org = await service.create_entity(
            EntityType.ORGANIZATION,
            org_data,
            "author:test",
            "Test",
            EntitySubType.POLITICAL_PARTY,
        )

        relationship = await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Initial",
        )

        # Update relationship
        relationship.attributes = {"role": "member"}
        await service.update_relationship(relationship, "author:test", "Added role")

        # Get versions
        versions = await service.get_relationship_versions(
            relationship_id=relationship.id
        )

        assert len(versions) == 2
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2

    @pytest.mark.asyncio
    async def test_author_tracking(self, temp_db_path):
        """Test that all changes track author attribution."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entity with specific author
        entity_data = {
            "slug": "author-test",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Author Test"}}],
        }
        entity = await service.create_entity(
            entity_type=EntityType.PERSON,
            entity_data=entity_data,
            author_id="author:specific-maintainer",
            change_description="Created by specific maintainer",
        )

        assert entity.version_summary.author.id == "author:specific-maintainer"

        # Update with different author
        entity.attributes = {"updated": "yes"}
        updated = await service.update_entity(
            entity=entity,
            author_id="author:different-maintainer",
            change_description="Updated by different maintainer",
        )

        assert updated.version_summary.author.id == "author:different-maintainer"


class TestPublicationServiceEntityPrefix:
    """Test entity_prefix support in Publication Service."""

    @pytest.mark.asyncio
    async def test_create_entity_with_entity_prefix(self, temp_db_path):
        """create_entity with entity_prefix creates entity with correct 3-level id."""
        from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES
        from nes.services.publication import PublicationService

        ALLOWED_ENTITY_PREFIXES.add("organization/nepal_govt/moha")
        try:
            db = FileDatabase(base_path=str(temp_db_path))
            service = PublicationService(database=db)

            entity_data = {
                "slug": "department-of-immigration",
                "names": [
                    {
                        "kind": "PRIMARY",
                        "en": {"full": "Department of Immigration"},
                        "ne": {"full": "आप्रवासन विभाग"},
                    }
                ],
            }

            entity = await service.create_entity(
                entity_prefix="organization/nepal_govt/moha",
                entity_data=entity_data,
                author_id="author:system-importer",
                change_description="Add MoHA department",
            )

            assert (
                entity.id
                == "entity:organization/nepal_govt/moha/department-of-immigration"
            )
            assert entity.entity_prefix == "organization/nepal_govt/moha"
            assert entity.slug == "department-of-immigration"
            assert entity.version_summary.version_number == 1
        finally:
            ALLOWED_ENTITY_PREFIXES.discard("organization/nepal_govt/moha")

    @pytest.mark.asyncio
    async def test_create_entity_old_style_still_works(self, temp_db_path):
        """create_entity with old entity_type/entity_subtype still works — backward compat."""
        from nes.services.publication import PublicationService

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        entity_data = {
            "slug": "nepali-congress",
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {"full": "Nepali Congress"},
                    "ne": {"full": "नेपाली कांग्रेस"},
                }
            ],
        }

        entity = await service.create_entity(
            entity_type=EntityType.ORGANIZATION,
            entity_subtype=EntitySubType.POLITICAL_PARTY,
            entity_data=entity_data,
            author_id="author:system-importer",
            change_description="Initial import",
        )

        assert entity.id == "entity:organization/political_party/nepali-congress"
        assert entity.entity_prefix is None

    @pytest.mark.asyncio
    async def test_entity_prefix_takes_precedence(self, temp_db_path):
        """entity_prefix takes precedence over entity_type/entity_subtype when both provided."""
        from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES
        from nes.services.publication import PublicationService

        ALLOWED_ENTITY_PREFIXES.add("organization/nepal_govt/moha")
        try:
            db = FileDatabase(base_path=str(temp_db_path))
            service = PublicationService(database=db)

            entity_data = {
                "slug": "passport-section",
                "names": [{"kind": "PRIMARY", "en": {"full": "Passport Section"}}],
            }

            entity = await service.create_entity(
                entity_prefix="organization/nepal_govt/moha",
                entity_type=EntityType.ORGANIZATION,
                entity_subtype=EntitySubType.GOVERNMENT_BODY,
                entity_data=entity_data,
                author_id="author:system-importer",
                change_description="Add passport section",
            )

            # entity_prefix should win
            assert entity.id == "entity:organization/nepal_govt/moha/passport-section"
            assert entity.entity_prefix == "organization/nepal_govt/moha"
        finally:
            ALLOWED_ENTITY_PREFIXES.discard("organization/nepal_govt/moha")

    @pytest.mark.asyncio
    async def test_create_entity_prefix_stored_and_retrievable(self, temp_db_path):
        """Entity created with entity_prefix is stored and can be retrieved by its new id."""
        from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES
        from nes.services.publication import PublicationService

        ALLOWED_ENTITY_PREFIXES.add("organization/nepal_govt/moha")
        try:
            db = FileDatabase(base_path=str(temp_db_path))
            service = PublicationService(database=db)

            entity_data = {
                "slug": "department-of-immigration",
                "names": [
                    {"kind": "PRIMARY", "en": {"full": "Department of Immigration"}}
                ],
            }

            entity = await service.create_entity(
                entity_prefix="organization/nepal_govt/moha",
                entity_data=entity_data,
                author_id="author:system-importer",
                change_description="Add MoHA department",
            )

            retrieved = await db.get_entity(entity.id)
            assert retrieved is not None
            assert (
                retrieved.id
                == "entity:organization/nepal_govt/moha/department-of-immigration"
            )
            assert retrieved.entity_prefix == "organization/nepal_govt/moha"
        finally:
            ALLOWED_ENTITY_PREFIXES.discard("organization/nepal_govt/moha")
