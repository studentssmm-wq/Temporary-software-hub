import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, String, func, Text, Integer
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

    # Зв'язок для отримання історії сканувань користувача
    scan_logs: Mapped[list["ScanLog"]] = relationship(
        "ScanLog",
        foreign_keys="[ScanLog.telegram_id]",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    coins: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    coin_transactions: Mapped[list["CoinTransaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Сума в гривнях (дорівнює кількості Єнот-токенів)"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        nullable=False,
        comment="PENDING, PAID, FAILED"
    )
    invoice_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        comment="ID інвойсу від Monobank для уникнення дублювання"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="payments"
    )


class CoinTransaction(Base):
    __tablename__ = "coin_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Може бути додатнім (поповнення) або від'ємним (витрата)"
    )
    feature: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Джерело: 'shop_topup', 'tarot', 'fortune_cookie', 'gift', 'other'"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="coin_transactions"
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


class ScanLog(Base):
    __tablename__ = "scan_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )

    scanner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="RESTRICT"),
        nullable=False,
    )

    action_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[telegram_id],
        back_populates="scan_logs",
    )

    scanner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[scanner_id],
    )


class ScheduledMailing(Base):
    __tablename__ = "scheduled_mailings"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    message_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    media_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    media_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    audience: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    send_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
