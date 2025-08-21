# db/models.py
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Boolean, DateTime, func, ForeignKey  # <- add ForeignKey


class Base(DeclarativeBase):
    pass


class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    mail: Mapped[str] = mapped_column(String, nullable=False)
    verification_code: Mapped[str] = mapped_column(String, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )


class Review(Base):
    __tablename__ = "hodnoceni"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    predmet: Mapped[str] = mapped_column(String, nullable=False)
    znamka: Mapped[str] = mapped_column(String, nullable=False)      # "A".."F"
    recenze: Mapped[str] = mapped_column(String, nullable=False)     # review text
    autor_id: Mapped[int] = mapped_column(Integer, nullable=False)   # discord user id
    # keep as TEXT for compatibility with old DB
    datum: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dislikes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class Reaction(Base):
    __tablename__ = "reakce"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hodnoceni_id: Mapped[int] = mapped_column(Integer, ForeignKey("hodnoceni.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    typ: Mapped[str] = mapped_column(String, nullable=False)         # "like" / "dislike"
    datum: Mapped[Optional[str]] = mapped_column(String, nullable=True)

