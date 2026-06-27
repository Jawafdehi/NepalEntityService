"""Health check endpoint for nes API.

This module provides a health check endpoint for monitoring:
- GET /api/health - Get API health status
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from nes.api.app import get_database, get_search_service
from nes.api.responses import HealthResponse
from nes.database.entity_database import EntityDatabase
from nes.services.search import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    database: EntityDatabase = Depends(get_database),
    search_service: SearchService = Depends(get_search_service),
):
    """Health check endpoint.

    Returns the current health status of the API and its dependencies,
    including database connectivity and version information.

    Returns:
        Health status information including:
        - Overall status (healthy/unhealthy)
        - API version
        - Database connectivity status
        - Timestamp
    """
    # Check database connectivity
    db_status = "connected"
    try:
        # Try to list entities to verify database is accessible
        await database.list_entities(limit=1)
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        db_status = "disconnected"

    # Report search backend status. A detached/absent backend means the API
    # is serving search from the database (degraded but healthy).
    backend = search_service.backend
    if backend is None:
        search_status = {"status": "database", "backend": "none"}
    else:
        try:
            healthy = await backend.health()
        except Exception:
            healthy = False
        search_status = {
            "status": "connected" if healthy else "disconnected",
            "backend": type(backend).__name__,
        }

    # Determine overall status (search degradation does not mark API unhealthy)
    overall_status = "healthy" if db_status == "connected" else "unhealthy"

    return HealthResponse(
        status=overall_status,
        version="2.0.0",
        api_version="v2",
        database={"status": db_status, "type": "file_database"},
        search=search_status,
        timestamp=datetime.now(UTC),
    )
