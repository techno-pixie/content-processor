from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.submission import Base

# SQLite for simplicity, but can be replaced with PostgreSQL for production
DATABASE_URL = "sqlite:///./submissions.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
