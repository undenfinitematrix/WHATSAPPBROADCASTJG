"""
AeroChat Broadcasts Module — Database Layer
=============================================
Async SQLAlchemy setup for MySQL with table definitions.

Requirements (add to requirements.txt):
    sqlalchemy[asyncio]>=2.0
    aiomysql

Usage:
    from broadcasts.database import get_session, broadcasts_table, recipients_table

    async with get_session() as session:
        result = await session.execute(select(broadcasts_table).where(...))

Setup:
    In your FastAPI app startup:

    from broadcasts.database import init_db, close_db

    @app.on_event("startup")
    async def startup():
        await init_db()

    @app.on_event("shutdown")
    async def shutdown():
        await close_db()
"""

from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    Enum,
    Index,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from contextlib import asynccontextmanager

from .config import settings


# =========================================
# Engine & Session
# =========================================

# Convert postgresql:// to postgresql+asyncpg:// if needed
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif not _db_url.startswith("postgresql+asyncpg://"):
    # If it's a placeholder, keep as-is (will fail on connect, not on import)
    pass

# Ensure SSL is set for Supabase (required for external connections)
if "supabase.co" in _db_url and "ssl" not in _db_url:
    _db_url += "?ssl=require" if "?" not in _db_url else "&ssl=require"

engine: AsyncEngine = None
SessionLocal: async_sessionmaker = None

metadata = MetaData()


async def init_db():
    """
    Initialize the async database engine and session factory.
    Called during FastAPI startup or lazily on first get_session() call.
    """
    global engine, SessionLocal

    if engine is not None:
        return  # Already initialized

    engine = create_async_engine(
        _db_url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,      # Verify connections before use
        pool_recycle=300,         # Recycle connections every 5 min (serverless-friendly)
        # Disable prepared statement caching — required for Supabase pgbouncer (transaction mode)
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
        echo=settings.LOG_LEVEL == "DEBUG",
    )

    SessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_db():
    """
    Close the database engine. Call this during FastAPI shutdown.
    """
    global engine
    if engine:
        await engine.dispose()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    Auto-initializes database if startup event didn't fire (Vercel serverless).

    Usage:
        async with get_session() as session:
            result = await session.execute(query)
            await session.commit()
    """
    if SessionLocal is None:
        await init_db()

    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =========================================
# Table Definitions
# =========================================

broadcasts_table = Table(
    settings.TABLE_BROADCASTS,
    metadata,
    Column("id", String(36), primary_key=True),
    Column("campaign_name", String(200), nullable=False),
    Column("template_name", String(200), nullable=True),
    Column("template_language", String(10), default="en"),
    Column("template_category", String(20), nullable=True),
    Column("status", String(20), nullable=False, default="draft", index=True),
    Column("audience_type", String(20), nullable=False, default="all"),
    Column("segment_id", String(36), nullable=True),
    Column("csv_file_id", String(36), nullable=True),
    Column("audience_label", String(200), nullable=True),
    Column("recipient_count", Integer, default=0),
    Column("schedule_type", String(20), default="now"),
    Column("scheduled_at", DateTime, nullable=True),
    Column("timezone", String(50), nullable=True),
    Column("sent_at", DateTime, nullable=True),
    Column("template_variables", JSON, nullable=True),
    Column("estimated_cost", Float, nullable=True),
    Column("actual_cost", Float, nullable=True),
    Column("message_preview", JSON, nullable=True),
    Column("created_at", DateTime, nullable=False, default=func.now()),
    Column("updated_at", DateTime, nullable=False, default=func.now(), onupdate=func.now()),

    # Indexes for common queries
    Index("idx_broadcasts_status_created", "status", "created_at"),
    Index("idx_broadcasts_sent_at", "sent_at"),
    Index("idx_broadcasts_campaign_name", "campaign_name"),
)


recipients_table = Table(
    settings.TABLE_BROADCAST_RECIPIENTS,
    metadata,
    Column("id", String(36), primary_key=True),
    Column("broadcast_id", String(36), ForeignKey(f"{settings.TABLE_BROADCASTS}.id", ondelete="CASCADE"), nullable=False),
    Column("contact_id", String(36), nullable=True),
    Column("phone", String(20), nullable=False),
    Column("meta_message_id", String(100), nullable=True),
    Column("status", String(20), nullable=False, default="pending"),
    Column("error_code", String(50), nullable=True),
    Column("error_message", Text, nullable=True),
    Column("sent_at", DateTime, nullable=True),
    Column("delivered_at", DateTime, nullable=True),
    Column("read_at", DateTime, nullable=True),
    Column("replied_at", DateTime, nullable=True),
    Column("failed_at", DateTime, nullable=True),
    Column("country_code", String(5), nullable=True),
    Column("created_at", DateTime, nullable=False, default=func.now()),
    Column("updated_at", DateTime, nullable=False, default=func.now(), onupdate=func.now()),

    # Critical indexes for webhook processing and analytics
    Index("idx_recipients_broadcast_id", "broadcast_id"),
    Index("idx_recipients_meta_message_id", "meta_message_id"),
    Index("idx_recipients_phone", "phone"),
    Index("idx_recipients_broadcast_status", "broadcast_id", "status"),
)


csv_uploads_table = Table(
    "csv_uploads",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("filename", String(255), nullable=False),
    Column("total_rows", Integer, default=0),
    Column("valid_phones", Integer, default=0),
    Column("invalid_phones", Integer, default=0),
    Column("duplicate_phones", Integer, default=0),
    Column("phones", JSON, nullable=True),       # List of validated phone numbers
    Column("errors", JSON, nullable=True),        # List of error messages
    Column("created_at", DateTime, nullable=False, default=func.now()),
)


# Contacts and Segments tables are assumed to already exist
# in your AeroChat database. These are reference definitions
# showing the columns the broadcasts module expects to query.
#
# If your existing tables use different column names, update
# the queries in the service files accordingly.

# contacts_table (EXPECTED TO EXIST):
#   id          VARCHAR(36)  PRIMARY KEY
#   name        VARCHAR(200)
#   phone       VARCHAR(20)
#   email       VARCHAR(200)
#   whatsapp_opted_in  BOOLEAN  DEFAULT FALSE
#   country_code       VARCHAR(5)
#   tags        JSON
#   created_at  DATETIME

# segments_table (EXPECTED TO EXIST):
#   id          VARCHAR(36)  PRIMARY KEY
#   name        VARCHAR(200)
#   description TEXT

# segment_members_table (EXPECTED TO EXIST):
#   segment_id  VARCHAR(36)
#   contact_id  VARCHAR(36)
#   PRIMARY KEY (segment_id, contact_id)


# =========================================
# Status Ranking Helper
# =========================================

# Used by webhook processing to enforce forward-only status updates.
# Higher rank = more advanced status.
STATUS_RANK = {
    "pending": 0,
    "sent": 1,
    "delivered": 2,
    "read": 3,
    "replied": 4,
    "failed": 5,   # Failed can overwrite anything (terminal state)
}


def status_is_advancement(current: str, new: str) -> bool:
    """
    Check if a status update is an advancement (forward progression).
    'failed' always counts as advancement (terminal override).
    """
    if new == "failed":
        return True
    return STATUS_RANK.get(new, 0) > STATUS_RANK.get(current, 0)
