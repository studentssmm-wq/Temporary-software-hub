from datetime import date
from sqlalchemy import BigInteger, Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

# Імпортуємо Base
from app.database.database import Base

if TYPE_CHECKING:
    from app.database.qr_pass import QRPass

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    institute: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    non_student_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    student_group: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    gender: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    birth_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    user_role: Mapped[str] = mapped_column(
        String(20),
        default="user",
    )

    data_consent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    qr_pass: Mapped["QRPass | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )