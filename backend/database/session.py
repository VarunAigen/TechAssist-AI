"""Database session management — supports both SQLite (dev) and PostgreSQL (prod).

Usage in FastAPI routes:
    from database.session import get_db
    
    @app.get("/items")
    async def list_items(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Item))
        return result.scalars().all()
"""

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from config import settings
from database.models import Base

import logging

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_async_session_factory = None


def _get_database_url() -> str:
    """Build the async database URL from settings.

    - If DATABASE_URL is set and starts with 'postgresql', converts to asyncpg format.
    - Otherwise falls back to SQLite with aiosqlite driver.
    """
    db_url = settings.DATABASE_URL

    if db_url and db_url.startswith("postgresql"):
        # Convert postgresql:// → postgresql+asyncpg://
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Default: SQLite for local dev
    sqlite_path = settings.SQLITE_DB_PATH
    return f"sqlite+aiosqlite:///{sqlite_path}"


def get_engine():
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        url = _get_database_url()
        is_sqlite = "sqlite" in url

        connect_args = {}
        if is_sqlite:
            connect_args["check_same_thread"] = False

        _engine = create_async_engine(
            url,
            echo=settings.ENVIRONMENT == "dev",  # SQL logging in dev only
            pool_pre_ping=True,
            connect_args=connect_args,
            # PostgreSQL pool settings (ignored for SQLite)
            **({"pool_size": 10, "max_overflow": 20} if not is_sqlite else {}),
        )
        logger.info(f"Database engine created: {'PostgreSQL' if not is_sqlite else 'SQLite'}")
    return _engine


def get_session_factory():
    """Get or create the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_db():
    """FastAPI dependency — yields an async database session.
    
    Automatically commits on success, rolls back on exception,
    and closes the session when done.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context():
    """Context manager version of get_db for non-FastAPI usage (e.g., startup scripts).
    
    Usage:
        async with get_db_context() as db:
            result = await db.execute(select(User))
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all database tables.
    
    In production, use Alembic migrations instead.
    This is a convenience for local development.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Auto-migration for SQLite queries table to add resolution columns if missing
    async with engine.begin() as conn:
        url = _get_database_url()
        if "sqlite" in url:
            try:
                from sqlalchemy import text
                result = await conn.execute(text("PRAGMA table_info(queries)"))
                columns = [row[1] for row in result.fetchall()]
                
                if "is_resolved" not in columns:
                    await conn.execute(text("ALTER TABLE queries ADD COLUMN is_resolved BOOLEAN DEFAULT 0 NOT NULL"))
                    logger.info("Database migration: Added is_resolved column to queries table")
                    
                if "resolved_answer" not in columns:
                    await conn.execute(text("ALTER TABLE queries ADD COLUMN resolved_answer TEXT"))
                    logger.info("Database migration: Added resolved_answer column to queries table")
            except Exception as e:
                logger.error(f"Failed to auto-migrate queries table: {e}")

    logger.info("Database tables created and initialized successfully")


async def close_db():
    """Close the database engine and clean up connections."""
    global _engine, _async_session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connections closed")
