"""Tests for Relationship Graph Traversal in nes.

Following TDD approach: Write failing tests first (Red phase).
These tests define the expected behavior of relationship graph traversal.

Graph traversal includes:
- Bidirectional traversal
- Depth-limited exploration
- Relationship path finding
- Graph visualization
"""

from datetime import date
from typing import Any, Dict, List

import pytest

from nes.core.models.entity import EntityType
from nes.database.file_database import FileDatabase


class TestBidirectionalTraversal:
    """Test bidirectional relationship traversal."""

    @pytest.mark.asyncio
    async def test_traverse_outgoing_relationships(self, temp_db_path):
        """Test traversing outgoing relationships from an entity."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import traverse_relationships

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities: person -> org1, person -> org2
        person_data = {
            "slug": "traverse-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Traverse Person"}}],
        }
        org1_data = {
            "slug": "org-1",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Org 1"}}],
        }
        org2_data = {
            "slug": "org-2",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Org 2"}}],
        }

        person = await service.create_entity(
     entity_prefix="person",
     entity_data=person_data,
     author_id="author:test",
     change_description="Test",
 )
        org1 = await service.create_entity(
     entity_prefix="organization/political_party",
     entity_data=org1_data,
     author_id="author:test",
     change_description="Test",
 )
        org2 = await service.create_entity(
     entity_prefix="organization/political_party",
     entity_data=org2_data,
     author_id="author:test",
     change_description="Test",
 )

        # Create relationships
        await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org1.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Member of org1",
        )

        await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org2.id,
            relationship_type="AFFILIATED_WITH",
            author_id="author:test",
            change_description="Affiliated with org2",
        )

        # Traverse outgoing relationships
        result = await traverse_relationships(
            db=db, entity_id=person.id, direction="outgoing", depth=1
        )

        assert len(result) == 2
        assert any(r["target_entity_id"] == org1.id for r in result)
        assert any(r["target_entity_id"] == org2.id for r in result)

    @pytest.mark.asyncio
    async def test_traverse_incoming_relationships(self, temp_db_path):
        """Test traversing incoming relationships to an entity."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import traverse_relationships

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities: person1 -> org, person2 -> org
        person1_data = {
            "slug": "person-1",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Person 1"}}],
        }
        person2_data = {
            "slug": "person-2",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Person 2"}}],
        }
        org_data = {
            "slug": "target-org",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Target Org"}}],
        }

        person1 = await service.create_entity(
     entity_prefix="person",
     entity_data=person1_data,
     author_id="author:test",
     change_description="Test",
 )
        person2 = await service.create_entity(
     entity_prefix="person",
     entity_data=person2_data,
     author_id="author:test",
     change_description="Test",
 )
        org = await service.create_entity(
     entity_prefix="organization/political_party",
     entity_data=org_data,
     author_id="author:test",
     change_description="Test",
 )

        # Create relationships
        await service.create_relationship(
            source_entity_id=person1.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Person1 member",
        )

        await service.create_relationship(
            source_entity_id=person2.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Person2 member",
        )

        # Traverse incoming relationships
        result = await traverse_relationships(
            db=db, entity_id=org.id, direction="incoming", depth=1
        )

        assert len(result) == 2
        assert any(r["source_entity_id"] == person1.id for r in result)
        assert any(r["source_entity_id"] == person2.id for r in result)

    @pytest.mark.asyncio
    async def test_traverse_both_directions(self, temp_db_path):
        """Test traversing relationships in both directions."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import traverse_relationships

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities: person1 -> person2 -> person3
        entities = []
        for i in range(1, 4):
            entity_data = {
                "slug": f"bidirectional-{i}",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": f"Person {i}"}}],
            }
            entity = await service.create_entity(
     entity_prefix="person",
     entity_data=entity_data,
     author_id="author:test",
     change_description="Test",
 )
            entities.append(entity)

        # Create relationships
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

        # Traverse both directions from middle entity
        result = await traverse_relationships(
            db=db, entity_id=entities[1].id, direction="both", depth=1
        )

        # Should find both incoming (from person1) and outgoing (to person3)
        assert len(result) == 2


class TestDepthLimitedExploration:
    """Test depth-limited relationship exploration."""

    @pytest.mark.asyncio
    async def test_traverse_depth_one(self, temp_db_path):
        """Test traversing relationships with depth limit of 1."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import traverse_relationships

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create chain: A -> B -> C
        entities = []
        for slug in ["depth-a", "depth-b", "depth-c"]:
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

        # Create relationships
        await service.create_relationship(
            source_entity_id=entities[0].id,
            target_entity_id=entities[1].id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="A -> B",
        )

        await service.create_relationship(
            source_entity_id=entities[1].id,
            target_entity_id=entities[2].id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="B -> C",
        )

        # Traverse with depth=1 from A
        result = await traverse_relationships(
            db=db, entity_id=entities[0].id, direction="outgoing", depth=1
        )

        # Should only find B, not C
        assert len(result) == 1
        assert result[0]["target_entity_id"] == entities[1].id

    @pytest.mark.asyncio
    async def test_traverse_depth_two(self, temp_db_path):
        """Test traversing relationships with depth limit of 2."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import traverse_relationships

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create chain: A -> B -> C -> D
        entities = []
        for slug in ["chain-a", "chain-b", "chain-c", "chain-d"]:
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

        # Create relationships
        for i in range(len(entities) - 1):
            await service.create_relationship(
                source_entity_id=entities[i].id,
                target_entity_id=entities[i + 1].id,
                relationship_type="SUPERVISES",
                author_id="author:test",
                change_description=f"{i} -> {i+1}",
            )

        # Traverse with depth=2 from A
        result = await traverse_relationships(
            db=db, entity_id=entities[0].id, direction="outgoing", depth=2
        )

        # Should find B and C, but not D
        assert len(result) == 2
        entity_ids = [r["target_entity_id"] for r in result]
        assert entities[1].id in entity_ids
        assert entities[2].id in entity_ids
        assert entities[3].id not in entity_ids

    @pytest.mark.asyncio
    async def test_traverse_unlimited_depth(self, temp_db_path):
        """Test traversing relationships with unlimited depth."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import traverse_relationships

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create long chain: A -> B -> C -> D -> E
        entities = []
        for i in range(5):
            entity_data = {
                "slug": f"unlimited-{i}",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": f"Person {i}"}}],
            }
            entity = await service.create_entity(
     entity_prefix="person",
     entity_data=entity_data,
     author_id="author:test",
     change_description="Test",
 )
            entities.append(entity)

        # Create relationships
        for i in range(len(entities) - 1):
            await service.create_relationship(
                source_entity_id=entities[i].id,
                target_entity_id=entities[i + 1].id,
                relationship_type="SUPERVISES",
                author_id="author:test",
                change_description=f"{i} -> {i+1}",
            )

        # Traverse with unlimited depth (depth=None or depth=-1)
        result = await traverse_relationships(
            db=db, entity_id=entities[0].id, direction="outgoing", depth=None
        )

        # Should find all entities in the chain
        assert len(result) == 4  # B, C, D, E


class TestRelationshipPathFinding:
    """Test finding paths between entities."""

    @pytest.mark.asyncio
    async def test_find_direct_path(self, temp_db_path):
        """Test finding a direct path between two entities."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import find_path

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create entities: A -> B
        entity_a_data = {
            "slug": "path-a",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Path A"}}],
        }
        entity_b_data = {
            "slug": "path-b",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Path B"}}],
        }

        entity_a = await service.create_entity(
     entity_prefix="person",
     entity_data=entity_a_data,
     author_id="author:test",
     change_description="Test",
 )
        entity_b = await service.create_entity(
     entity_prefix="person",
     entity_data=entity_b_data,
     author_id="author:test",
     change_description="Test",
 )

        # Create relationship
        await service.create_relationship(
            source_entity_id=entity_a.id,
            target_entity_id=entity_b.id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="A -> B",
        )

        # Find path from A to B
        path = await find_path(
            db=db, source_entity_id=entity_a.id, target_entity_id=entity_b.id
        )

        assert path is not None
        assert len(path) == 1
        assert path[0]["source_entity_id"] == entity_a.id
        assert path[0]["target_entity_id"] == entity_b.id

    @pytest.mark.asyncio
    async def test_find_multi_hop_path(self, temp_db_path):
        """Test finding a multi-hop path between entities."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import find_path

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create chain: A -> B -> C -> D
        entities = []
        for slug in ["multi-a", "multi-b", "multi-c", "multi-d"]:
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

        # Create relationships
        for i in range(len(entities) - 1):
            await service.create_relationship(
                source_entity_id=entities[i].id,
                target_entity_id=entities[i + 1].id,
                relationship_type="SUPERVISES",
                author_id="author:test",
                change_description=f"{i} -> {i+1}",
            )

        # Find path from A to D
        path = await find_path(
            db=db, source_entity_id=entities[0].id, target_entity_id=entities[3].id
        )

        assert path is not None
        assert len(path) == 3  # A->B, B->C, C->D

    @pytest.mark.asyncio
    async def test_find_shortest_path(self, temp_db_path):
        """Test finding the shortest path when multiple paths exist."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import find_path

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create graph with multiple paths:
        # A -> B -> D
        # A -> C -> D
        entities = []
        for slug in ["shortest-a", "shortest-b", "shortest-c", "shortest-d"]:
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

        # Create relationships for both paths
        await service.create_relationship(
            source_entity_id=entities[0].id,
            target_entity_id=entities[1].id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="A -> B",
        )

        await service.create_relationship(
            source_entity_id=entities[1].id,
            target_entity_id=entities[3].id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="B -> D",
        )

        await service.create_relationship(
            source_entity_id=entities[0].id,
            target_entity_id=entities[2].id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="A -> C",
        )

        await service.create_relationship(
            source_entity_id=entities[2].id,
            target_entity_id=entities[3].id,
            relationship_type="SUPERVISES",
            author_id="author:test",
            change_description="C -> D",
        )

        # Find shortest path from A to D (both paths have length 2)
        path = await find_path(
            db=db, source_entity_id=entities[0].id, target_entity_id=entities[3].id
        )

        assert path is not None
        assert len(path) == 2  # Should be shortest path

    @pytest.mark.asyncio
    async def test_no_path_exists(self, temp_db_path):
        """Test when no path exists between entities."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import find_path

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create disconnected entities
        entity_a_data = {
            "slug": "disconnected-a",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Disconnected A"}}],
        }
        entity_b_data = {
            "slug": "disconnected-b",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Disconnected B"}}],
        }

        entity_a = await service.create_entity(
     entity_prefix="person",
     entity_data=entity_a_data,
     author_id="author:test",
     change_description="Test",
 )
        entity_b = await service.create_entity(
     entity_prefix="person",
     entity_data=entity_b_data,
     author_id="author:test",
     change_description="Test",
 )

        # No relationship between them

        # Find path (should return None)
        path = await find_path(
            db=db, source_entity_id=entity_a.id, target_entity_id=entity_b.id
        )

        assert path is None


class TestGraphVisualization:
    """Test graph visualization generation."""

    @pytest.mark.asyncio
    async def test_generate_dot_format(self, temp_db_path):
        """Test generating graph in DOT format for Graphviz."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import generate_graph_visualization

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create simple graph
        person_data = {
            "slug": "viz-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Viz Person"}}],
        }
        org_data = {
            "slug": "viz-org",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Viz Org"}}],
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

        await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Member",
        )

        # Generate DOT format
        dot_output = await generate_graph_visualization(
            db=db, entity_id=person.id, format="dot", depth=1
        )

        assert dot_output is not None
        assert "digraph" in dot_output
        assert person.id in dot_output
        assert org.id in dot_output

    @pytest.mark.asyncio
    async def test_generate_mermaid_format(self, temp_db_path):
        """Test generating graph in Mermaid format."""
        from nes.services.publication import PublicationService
        from nes.services.publication.graph import generate_graph_visualization

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create simple graph
        person_data = {
            "slug": "mermaid-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "Mermaid Person"}}],
        }
        org_data = {
            "slug": "mermaid-org",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "Mermaid Org"}}],
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

        await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Member",
        )

        # Generate Mermaid format
        mermaid_output = await generate_graph_visualization(
            db=db, entity_id=person.id, format="mermaid", depth=1
        )

        assert mermaid_output is not None
        assert "graph" in mermaid_output.lower()
        assert "-->" in mermaid_output or "---" in mermaid_output

    @pytest.mark.asyncio
    async def test_generate_json_format(self, temp_db_path):
        """Test generating graph in JSON format."""
        import json

        from nes.services.publication import PublicationService
        from nes.services.publication.graph import generate_graph_visualization

        db = FileDatabase(base_path=str(temp_db_path))
        service = PublicationService(database=db)

        # Create simple graph
        person_data = {
            "slug": "json-person",
            "type": "person",
            "names": [{"kind": "PRIMARY", "en": {"full": "JSON Person"}}],
        }
        org_data = {
            "slug": "json-org",
            "type": "organization",
            "names": [{"kind": "PRIMARY", "en": {"full": "JSON Org"}}],
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

        await service.create_relationship(
            source_entity_id=person.id,
            target_entity_id=org.id,
            relationship_type="MEMBER_OF",
            author_id="author:test",
            change_description="Member",
        )

        # Generate JSON format
        json_output = await generate_graph_visualization(
            db=db, entity_id=person.id, format="json", depth=1
        )

        assert json_output is not None
        # Should be valid JSON
        data = json.loads(json_output)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 2
        assert len(data["edges"]) >= 1
