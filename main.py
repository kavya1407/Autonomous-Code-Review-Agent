"""Root application entrypoint allowing `uvicorn main:app --reload` execution."""

from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
