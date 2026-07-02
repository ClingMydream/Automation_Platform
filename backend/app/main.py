"""FastAPI application entrypoint for backend startup, middleware, and route mounting."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db import Base, engine
from app.models import entities  # noqa: F401


# FastAPI instance is the backend HTTP application mounted by Uvicorn.
app = FastAPI(title="Automation Platform API")

# CORS is permissive for the first version so the frontend can call the API from Nginx or local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Create database tables and ensure the default administrator account exists."""
    # SQLAlchemy creates missing tables at startup so a fresh Docker database can boot automatically.
    Base.metadata.create_all(bind=engine)


# All feature routers are grouped under /api for a clean Nginx reverse-proxy rule.
app.include_router(router, prefix="/api")
