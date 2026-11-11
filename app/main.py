"""FastAPI Application Entrypoint for Autonomous Code Review & Refactoring Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context."""
    yield


app = FastAPI(
    title="Autonomous Code Review & Refactoring Agent",
    description=(
        "Stateful, human-in-the-loop code review and refactoring service powered by LangGraph, "
        "sandboxed flake8/black linting, GitHub Webhooks, and automated Git commits."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Enable CORS for external webhook dispatchers / dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health status and configuration inspection endpoint."""
    return {
        "status": "healthy",
        "service": "Autonomous Code Review & Refactoring Agent",
        "environment": settings.app_env,
        "persistence_type": settings.persistence_type,
        "llm_provider": settings.llm_provider,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
