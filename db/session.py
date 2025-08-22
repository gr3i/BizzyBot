# db/session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# read DATABASE_URL from env, eg:
#   sqlite:////app/db/app.db
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# echo=False to keep logs clean. For debug set echo=True
engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
)

# expire_on_commit=False so objects keep values after commit
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)

