# db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Muzu prepnout pres promennou prostredi DATABASE_URL, jinak spadne na SQLite v db/app.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db/app.db")

# Rada: U SQLite na Discord botech se hodi check_same_thread=False
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

