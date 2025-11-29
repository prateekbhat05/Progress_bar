# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use SQLite for easy local / online testing (Codespaces / Replit)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# SQLite needs this flag for multi-threaded use in the same process
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
