from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite:///./reviews.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


class ReviewRecord(Base):
    """SQLAlchemy model to persist code review results."""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(Text, nullable=False)
    language = Column(String(50), default="Python")
    quality_score = Column(String(10))
    issues = Column(Text)
    ai_explanation = Column(Text)
    fixed_code = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully.")
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
        logger.error(f"Unexpected error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
