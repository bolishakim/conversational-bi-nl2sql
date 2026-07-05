"""
NL2SQL AI Agent Backend - Main Entry Point
FastAPI application with health check and CORS configuration
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import settings, validate_settings
from api.auth import router as auth_router
from api.chat import router as chat_router
from api.history import router as history_router
from api.dashboards import router as dashboards_router
from api.experiment import router as experiment_router
from api.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    print("\n" + "=" * 80)
    print("Starting NL2SQL AI Agent Backend")
    print("=" * 80)

    try:
        validate_settings()
        print(f"[OK] Configuration validated")
        print(f"[OK] API Server: {settings.API_HOST}:{settings.API_PORT}")
        print(f"[OK] Database: {settings.DATABASE_NAME}")
        print(f"[OK] Debug Mode: {settings.DEBUG}")
        print("=" * 80 + "\n")
    except ValueError as e:
        print(f"[FAIL] Configuration validation failed: {e}")
        raise

    yield

    # Shutdown
    print("\n" + "=" * 80)
    print("Shutting down NL2SQL AI Agent Backend")
    print("=" * 80 + "\n")


# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(history_router)
app.include_router(dashboards_router)
app.include_router(experiment_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "description": settings.API_DESCRIPTION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    Returns service status and configuration info
    """
    return {
        "status": "healthy",
        "service": "nl2sql-backend",
        "version": settings.API_VERSION,
        "database": {
            "host": settings.DATABASE_HOST,
            "port": settings.DATABASE_PORT,
            "name": settings.DATABASE_NAME
        },
        "configuration": {
            "debug": settings.DEBUG,
            "embedding_model": settings.EMBEDDING_MODEL,
            "llm_model": settings.LLM_MODEL,
            "top_k_tables": settings.TOP_K_TABLES,
            "anchor_tables_enabled": settings.ENABLE_ANCHOR_TABLES
        }
    }


@app.get("/api/v1/status")
async def api_status():
    """
    API status endpoint
    Provides detailed service information
    """
    return {
        "api_version": "v1",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "query": "/api/v1/query (coming soon)",
            "history": "/api/v1/history (coming soon)",
            "schema": "/api/v1/schema (coming soon)"
        },
        "features": {
            "rag_retrieval": True,
            "anchor_tables": settings.ENABLE_ANCHOR_TABLES,
            "domain_detection": True,
            "sql_generation": "coming soon",
            "visualization": "coming soon"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )
