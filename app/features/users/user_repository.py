from uuid import UUID
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import User, QRPass


async def find_user_by_id(session: AsyncSession, id: UUID) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == id)
    )
    user = result.scalar_one_or_none()
    return user


async def update_user_role(session: AsyncSession, id: int, role: str):
    user = await find_user_by_id(session, id)
    if not user:
        return None
    user.user_role = role
    await session.commit()
    await session.refresh(user)
    return user


async def get_users_for_broadcast(session: AsyncSession, target: str) -> list[int]:
    if target == "all":
        result = await session.execute(select(User.telegram_id))
    elif target == "on":
        result = await session.execute(
            select(QRPass.telegram_id).where(QRPass.is_on_territory == True)
        )
    elif target == "off":
        result = await session.execute(
            select(QRPass.telegram_id).where(QRPass.is_on_territory == False)
        )
    else:
        return []

    return list(result.scalars().all())


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    first_name: str,
    last_name: str | None,
    institute: str | None,
    non_student_type: str | None,
    student_group: str | None,
    gender: str,
    birth_date: date,
    username: str | None,
    data_consent: bool
) -> User:
    new_user = User(
        telegram_id=telegram_id,
        first_name=first_name,
        last_name=last_name,
        institute=institute,
        non_student_type=non_student_type,
        student_group=student_group,
        gender=gender,
        birth_date=birth_date,
        username=username,
        data_consent=data_consent
    )
    session.add(new_user)
    await session.commit()
    return new_user
