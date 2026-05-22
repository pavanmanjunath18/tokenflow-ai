import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.api import integrations, dashboard, licenses, recommendations, audit, governance, infrastructure
from app.api import auth as auth_router
from app.api import tasks as tasks_router
from app.api import system as system_router

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)


def _seed_default_admin():
    """Create a default admin user on first boot if no users exist."""
    from sqlalchemy.orm import Session
    from app.models.user import User
    from app.core.security import hash_password

    with Session(engine) as db:
        if db.query(User).count() == 0:
            admin = User(
                email=settings.default_admin_email,
                hashed_password=hash_password(settings.default_admin_password),
                full_name="Platform Admin",
                role="admin",
            )
            db.add(admin)
            db.commit()
            logger.warning(
                "Created default admin user: %s — change the password before production use",
                settings.default_admin_email,
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (use `alembic upgrade head` for schema migrations in production)
    Base.metadata.create_all(bind=engine)
    _seed_default_admin()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="TokenFlow AI",
    description="Enterprise AI Cost, Usage & Governance Intelligence Platform",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router,     prefix="/api")
app.include_router(integrations.router,    prefix="/api")
app.include_router(dashboard.router,       prefix="/api")
app.include_router(licenses.router,        prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(governance.router,      prefix="/api")
app.include_router(infrastructure.router,  prefix="/api")
app.include_router(audit.router,           prefix="/api")
app.include_router(tasks_router.router,    prefix="/api")
app.include_router(system_router.router,   prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}
