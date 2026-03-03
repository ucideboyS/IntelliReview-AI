from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import logging
import os

logger = logging.getLogger(__name__)

# ── DATABASE URL ───────────────────────────────────────────────────────────
# If DATABASE_URL is set in environment → use it (PostgreSQL in production)
# Otherwise → fallback to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reviews.db")

# PostgreSQL via DATABASE_URL does not need check_same_thread
_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


class ReviewRecord(Base):
    """SQLAlchemy model to persist multi-dimensional code review results."""
    __tablename__ = "reviews"

    id              = Column(Integer, primary_key=True, index=True)
    code            = Column(Text, nullable=False)
    language        = Column(String(50), default="Python")

    # Multi-dimensional scores (0.0 – 10.0)
    readability     = Column(Float, default=0.0)
    performance     = Column(Float, default=0.0)
    maintainability = Column(Float, default=0.0)
    security        = Column(Float, default=0.0)
    best_practices  = Column(Float, default=0.0)
    overall_score   = Column(Float, default=0.0)

    # Text results
    issues          = Column(Text)
    ai_explanation  = Column(Text)
    fixed_code      = Column(Text)

    # Token usage tracking (nullable for backward compat with old records)
    token_usage     = Column(Integer, nullable=True)

    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database initialized successfully. Using: "
                    f"{'PostgreSQL' if 'postgresql' in DATABASE_URL else 'SQLite'}")
    except SQLAlchemyError as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def get_db():
    """Database dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in DB session: {e}")
        db.rollback()
        raise
    finally:
        db.close()