import uuid
from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


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


class QRPass(Base):
    __tablename__ = "qr_passes"

    pass_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    is_on_territory: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="qr_pass",
    )

class BotMedia(Base):
    __tablename__ = "bot_media"

    # Назва медіа, наприклад "map" або "schedule"
    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    # Унікальний код файлу в Telegram
    file_id: Mapped[str] = mapped_column(String(255), nullable=False)

class ScheduleMedia(Base):
    __tablename__ = "schedule_media"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_day: Mapped[int] = mapped_column(nullable=False)
    file_id: Mapped[str] = mapped_column(String(255), nullable=False)