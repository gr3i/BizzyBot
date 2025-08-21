from datetime import datetime
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Boolean, DateTime, func, ForeignKey

class Base(DeclarativeBase):
    pass

# ----- VERIFICATION -----
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

# ----- REVIEWS -----
class Review(Base):
    __tablename__ = "hodnoceni"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    predmet: Mapped[str] = mapped_column(String, nullable=False)
    znamka: Mapped[str] = mapped_column(String, nullable=False)
    recenze: Mapped[str] = mapped_column(String, nullable=False)
    autor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    datum: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dislikes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

class Reaction(Base):
    __tablename__ = "reakce"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hodnoceni_id: Mapped[int] = mapped_column(Integer, ForeignKey("hodnoceni.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    typ: Mapped[str] = mapped_column(String, nullable=False)  # "like" / "dislike"
    datum: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")

