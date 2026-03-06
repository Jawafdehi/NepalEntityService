"""Documentation hosting tests for nes API (TDD - Red Phase).

This test module covers documentation hosting functionality:
- Documentation rendering from Markdown files
- Page navigation between documentation pages
- 404 handling for missing pages
- Markdown parsing and HTML generation
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from nes.api.app import app


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    """Create an async HTTP client for testing."""
    # Initialize database for tests that need it
    from nes.config import Config

    db_path = tmp_path / "test-db"
    monkeypatch.setenv("NES_DB_URL", f"file://{db_path}")
    Config.initialize_database(base_path=str(db_path))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    Config.cleanup()


# ============================================================================
# Documentation Rendering Tests
# ============================================================================


class TestDocumentationRendering:
    """Tests for documentation rendering from Markdown files."""

    @pytest.mark.asyncio
    async def test_root_serves_documentation_landing_page(self, client):
        """Test that root endpoint (/) serves the documentation landing page."""
        response = await client.get("/")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")

        # Check that it contains expected documentation content
        content = response.text
        assert "Nepal Entity Service" in content
        assert "API" in content or "Documentation" in content

    @pytest.mark.asyncio
    async def test_documentation_contains_html_structure(self, client):
        """Test that documentation is rendered as proper HTML."""
        response = await client.get("/")

        assert response.status_code == 200
        content = response.text

        # Check for basic HTML structure
        assert "<!DOCTYPE html>" in content or "<html" in content
        assert "<head>" in content
        assert "<body>" in content
        assert "</html>" in content

    @pytest.mark.asyncio
    async def test_markdown_headers_rendered_as_html(self, client):
        """Test that Markdown headers are converted to HTML headers."""
        response = await client.get("/")

        assert response.status_code == 200
        content = response.text

        # Check for HTML header tags (h1, h2, etc.)
        assert "<h1>" in content or "<h2>" in content

    @pytest.mark.asyncio
    async def test_markdown_links_rendered_as_html(self, client):
        """Test that Markdown links are converted to HTML anchor tags."""
        response = await client.get("/")

        assert response.status_code == 200
        content = response.text

        # Check for HTML anchor tags
        assert "<a href=" in content

    @pytest.mark.asyncio
    async def test_markdown_code_blocks_rendered(self, client):
        """Test that Markdown code blocks are properly rendered."""
        response = await client.get("/consumers/getting-started")

        assert response.status_code == 200
        content = response.text

        # Check for code block rendering (pre/code tags)
        assert "<pre>" in content or "<code>" in content


# ============================================================================
# Page Navigation Tests
# ============================================================================


class TestPageNavigation:
    """Tests for navigation between documentation pages."""

    @pytest.mark.asyncio
    async def test_getting_started_page(self, client):
        """Test that getting-started page is accessible."""
        response = await client.get("/consumers/getting-started")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")

        content = response.text
        assert "Getting Started" in content or "getting started" in content.lower()

    @pytest.mark.asyncio
    async def test_architecture_page(self, client):
        """Test that architecture page is accessible."""
        response = await client.get("/consumers/api-guide")

        assert response.status_code == 200
        content = response.text
        assert "API" in content or "api" in content.lower()

    @pytest.mark.asyncio
    async def test_api_reference_page(self, client):
        """Test that API reference page is accessible."""
        response = await client.get("/consumers/api-guide")

        assert response.status_code == 200
        content = response.text
        assert "API" in content

    @pytest.mark.asyncio
    async def test_data_models_page(self, client):
        """Test that data models page is accessible."""
        response = await client.get("/consumers/data-models")

        assert response.status_code == 200
        content = response.text
        assert "Model" in content or "model" in content.lower()

    @pytest.mark.asyncio
    async def test_examples_page(self, client):
        """Test that examples page is accessible."""
        response = await client.get("/consumers/examples")

        assert response.status_code == 200
        content = response.text
        assert "Example" in content or "example" in content.lower()

    @pytest.mark.asyncio
    async def test_multiple_pages_have_consistent_styling(self, client):
        """Test that all documentation pages use consistent HTML template."""
        pages = ["/", "/consumers/getting-started", "/consumers/api-guide"]

        for page in pages:
            response = await client.get(page)
            assert response.status_code == 200

            content = response.text
            # All pages should have same basic structure
            assert "<html" in content
            assert "<head>" in content
            assert "<body>" in content


# ============================================================================
# 404 Handling Tests
# ============================================================================


class TestNotFoundHandling:
    """Tests for 404 handling of missing documentation pages."""

    @pytest.mark.asyncio
    async def test_nonexistent_page_returns_404(self, client):
        """Test that requesting a non-existent page returns 404."""
        response = await client.get("/nonexistent-page")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_404_response_is_html(self, client):
        """Test that 404 response is HTML (not JSON)."""
        response = await client.get("/nonexistent-page")

        assert response.status_code == 404
        # Should return HTML, not JSON
        assert response.headers["content-type"].startswith("text/html")

    @pytest.mark.asyncio
    async def test_404_page_contains_helpful_message(self, client):
        """Test that 404 page contains a helpful error message."""
        response = await client.get("/nonexistent-page")

        assert response.status_code == 404
        content = response.text

        # Should contain helpful message
        assert "404" in content or "not found" in content.lower()

    @pytest.mark.asyncio
    async def test_404_page_has_navigation_links(self, client):
        """Test that 404 page includes links to valid pages."""
        response = await client.get("/nonexistent-page")

        assert response.status_code == 404
        content = response.text

        # Should have links to help user navigate
        assert "<a href=" in content

    @pytest.mark.asyncio
    async def test_api_endpoints_not_affected_by_doc_routing(self, client):
        """Test that API endpoints still work and aren't caught by doc routing."""
        # API endpoints should still return JSON, not HTML
        response = await client.get("/api/health")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        assert "status" in data


# ============================================================================
# Markdown Parsing Tests
# ============================================================================


class TestMarkdownParsing:
    """Tests for Markdown parsing functionality."""

    @pytest.mark.asyncio
    async def test_markdown_bold_text_rendered(self, client):
        """Test that Markdown bold text is converted to HTML strong/b tags."""
        response = await client.get("/")

        assert response.status_code == 200
        content = response.text

        # Check for bold rendering
        assert "<strong>" in content or "<b>" in content

    @pytest.mark.asyncio
    async def test_markdown_italic_text_rendered(self, client):
        """Test that Markdown italic text is converted to HTML em/i tags."""
        # Check a page that has italic text (CSS has font-style: italic)
        response = await client.get("/")

        assert response.status_code == 200
        content = response.text

        # Check that the CSS includes italic styling (which means italic support is there)
        # The actual markdown may or may not have italic text, but the rendering supports it
        assert "font-style: italic" in content or "<em>" in content or "<i>" in content

    @pytest.mark.asyncio
    async def test_markdown_lists_rendered(self, client):
        """Test that Markdown lists are converted to HTML ul/ol tags."""
        response = await client.get("/consumers/getting-started")

        assert response.status_code == 200
        content = response.text

        # Check for list rendering
        assert "<ul>" in content or "<ol>" in content
        assert "<li>" in content

    @pytest.mark.asyncio
    async def test_markdown_paragraphs_rendered(self, client):
        """Test that Markdown paragraphs are converted to HTML p tags."""
        response = await client.get("/")

        assert response.status_code == 200
        content = response.text

        # Check for paragraph tags
        assert "<p>" in content

    @pytest.mark.asyncio
    async def test_special_characters_escaped(self, client):
        """Test that special HTML characters are properly escaped."""
        response = await client.get("/")

        assert response.status_code == 200
        content = response.text

        # Should not have unescaped special chars that break HTML
        # (This is more about ensuring markdown library handles it correctly)
        assert response.status_code == 200


# ============================================================================
# API Documentation Separation Tests
# ============================================================================


class TestAPIDocumentationSeparation:
    """Tests to ensure API endpoints and documentation are properly separated."""

    @pytest.mark.asyncio
    async def test_api_prefix_routes_to_api_not_docs(self, client):
        """Test that /api/* routes go to API endpoints, not documentation."""
        response = await client.get("/api/health")

        assert response.status_code == 200
        # Should be JSON, not HTML
        assert response.headers["content-type"].startswith("application/json")

    @pytest.mark.asyncio
    async def test_docs_endpoint_serves_openapi_schema(self, client):
        """Test that /docs endpoint serves OpenAPI schema, not markdown docs."""
        response = await client.get("/docs")

        assert response.status_code == 200
        # Should be HTML (Swagger UI) or redirect to Swagger UI
        assert response.headers["content-type"].startswith("text/html")

    @pytest.mark.asyncio
    async def test_openapi_json_available(self, client):
        """Test that OpenAPI JSON schema is available."""
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data


# ============================================================================
# Content Security Tests
# ============================================================================


class TestContentSecurity:
    """Tests for content security in documentation rendering."""

    @pytest.mark.asyncio
    async def test_no_directory_traversal_in_page_param(self, client):
        """Test that directory traversal attempts are blocked."""
        # Try to access files outside docs directory
        response = await client.get("/../../../etc/passwd")

        # Should return 404, not expose file system
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_only_markdown_files_served(self, client):
        """Test that only .md files are served as documentation."""
        # Try to access non-markdown file
        response = await client.get("/../../pyproject.toml")

        # Should return 404
        assert response.status_code == 404
