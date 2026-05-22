import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.api import integrations, dashboard, licenses, recommendations, audit, governance, infrastructure

logging.basicConfig(level=settings.log_level.upper())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on first boot (use Alembic for production migrations)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="TokenFlow AI",
    description="Enterprise AI Cost, Usage & Governance Intelligence Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(integrations.router,    prefix="/api")
app.include_router(dashboard.router,       prefix="/api")
app.include_router(licenses.router,        prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(governance.router,      prefix="/api")
app.include_router(infrastructure.router,  prefix="/api")
app.include_router(audit.router,           prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
