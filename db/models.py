# db/models.py
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    func,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# verification table (zachovat data)
class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    mail: Mapped[str] = mapped_column(String, nullable=False, index=True)
    verification_code: Mapped[str] = mapped_column(String, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )

    __table_args__ = (
        Index("ix_verifications_user_id_created", "user_id", "created_at"),
    )


# reviews schema 
class Review(Base):
    __tablename__ = "hodnoceni"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    predmet: Mapped[str] = mapped_column(String, nullable=False, index=True)
    znamka: Mapped[str] = mapped_column(String(2), nullable=False)  # A..F
    recenze: Mapped[str] = mapped_column(String, nullable=False)
    autor_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # for compatibility I can keep string timestamp; here keep simple string
    datum: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dislikes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    reactions: Mapped[List["Reaction"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_hodnoceni_predmet_id", "predmet", "id"),
    )


class Reaction(Base):
    __tablename__ = "reakce"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hodnoceni_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hodnoceni.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    typ: Mapped[str] = mapped_column(String(16), nullable=False)  # like / dislike
    datum: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    review: Mapped[Review] = relationship(back_populates="reactions")

    __table_args__ = (
        UniqueConstraint("hodnoceni_id", "user_id", name="uq_reakce_review_user"),
        Index("ix_reakce_user", "user_id"),
    )

