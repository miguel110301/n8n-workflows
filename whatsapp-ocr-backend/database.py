"""SQLAlchemy engine and session setup, shared by models.py and main.py."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a session and guarantees it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
