"""FastAPI application for nes API.

This module creates and configures the FastAPI application with:
- CORS middleware for cross-origin requests
- Error handling middleware
- Dependency injection for services
- API routes under /api prefix
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from nes import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Nepal Entity Service API v2")

    # Initialize database
    db = config.Config.initialize_database(base_path="./nes-db/v2")

    # Warm cache for InMemoryCachedReadDatabase by triggering a sample query
    import sys
    import time

    from nes.database.in_memory_cached_read_database import InMemoryCachedReadDatabase

    if isinstance(db, InMemoryCachedReadDatabase):
        logger.info("Warming in-memory cache...")
        start_time = time.time()
        try:
            # Trigger cache warming with a sample entity lookup
            await db.get_entity("entity:person/bishweshwar-prasad-koirala")
            elapsed_time = time.time() - start_time
            logger.info(
                f"In-memory cache warmed successfully in {elapsed_time:.2f} seconds"
            )
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.warning(
                f"Cache warming completed with note in {elapsed_time:.2f} seconds: {e}"
            )

    # Initialize the search backend (if configured) and ensure its index exists.
    # If the backend is unreachable, degrade gracefully: detach it from the
    # search service so requests fall back to database search instead of failing.
    backend = config.Config.get_search_backend()
    if backend is not None:
        try:
            if await backend.health():
                await backend.ensure_index()
                logger.info("Search backend ready: %s", type(backend).__name__)
            else:
                raise RuntimeError("search backend health check failed")
        except Exception as e:
            logger.warning(
                "Search backend unavailable (%s); degrading to database search", e
            )
            config.Config.get_search_service().backend = None

    yield

    # Shutdown
    logger.info("Shutting down Nepal Entity Service API v2")
    if backend is not None:
        try:
            await backend.close()
        except Exception:
            logger.warning("Error closing search backend", exc_info=True)
    config.Config.cleanup()


# Create FastAPI application
app = FastAPI(
    title="Nepal Entity Service API",
    description="RESTful API for accessing Nepali public entity data",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================================
# Dependency Injection
# ============================================================================

# Import dependency functions from Config class
get_database = config.Config.get_database
get_search_service = config.Config.get_search_service
get_publication_service = config.Config.get_publication_service


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
            }
        },
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Data validation failed",
                "details": errors,
            }
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": {"code": "INVALID_REQUEST", "message": str(exc)}},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred"}
        },
    )


# ============================================================================
# API Routes
# ============================================================================

# Import and include routers
from nes.api.routes import entities, health, relationships, schemas  # noqa: E402

app.include_router(entities.router)
app.include_router(relationships.router)
app.include_router(schemas.router)
app.include_router(health.router)


# ============================================================================
# Documentation Endpoints (Must be last to avoid route conflicts)
# ============================================================================

from fastapi.responses import HTMLResponse  # noqa: E402

from nes.api.documentation import serve_documentation  # noqa: E402


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the documentation landing page."""
    return await serve_documentation("")


@app.get("/{page:path}", response_class=HTMLResponse)
async def documentation_page(page: str):
    """Serve a documentation page.

    This endpoint serves documentation pages from Markdown files.
    It should be registered after all other routes to avoid conflicts.
    The :path converter allows capturing nested paths with slashes.
    """
    return await serve_documentation(page)
