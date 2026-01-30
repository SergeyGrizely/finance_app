from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import DATABASE_URL

# Явно указываем psycopg2 диалект
db_url = DATABASE_URL
if "postgresql://" in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
elif "postgres://" in db_url:
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://")

engine = create_engine(db_url, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()