import uuid
from sqlalchemy import BigInteger, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

# Імпортуємо Base
from app.database.database import Base

if TYPE_CHECKING:
    from app.database.user import User


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