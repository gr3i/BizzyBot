# db/models.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Boolean, DateTime, func

class Base(DeclarativeBase):
    """Zaklad pro vsechny ORM modely."""
    pass

class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    mail: Mapped[str] = mapped_column(String, nullable=False)
    verification_code: Mapped[str] = mapped_column(String, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # timestamp necham vytvorit databazi (CURRENT_TIMESTAMP)
    created_at: Mapped["datetime"] = mapped_column(DateTime, server_default=func.current_timestamp())

