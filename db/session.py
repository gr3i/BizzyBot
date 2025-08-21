import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def _default_sqlite_url() -> str:
    # absolutni cesta v containeru
    return "sqlite:////app/db/app.db"

DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or _default_sqlite_url()

# u SQLite je treba check_same_thread=False pro vice vlaken (discord bot)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

