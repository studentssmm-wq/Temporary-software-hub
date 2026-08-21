from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Song


async def get_all_songs(session: AsyncSession) -> list[Song]:
    result = await session.execute(select(Song).order_by(Song.title))
    return list(result.scalars().all())


async def get_song_by_id(session: AsyncSession, song_id: int) -> Song | None:
    result = await session.execute(select(Song).where(Song.id == song_id))
    return result.scalar_one_or_none()


async def create_song(session: AsyncSession, title: str, lyrics: str) -> Song:
    song = Song(title=title, lyrics=lyrics)
    session.add(song)
    await session.commit()
    await session.refresh(song)
    return song


async def update_song(
    session: AsyncSession, song_id: int, title: str | None = None, lyrics: str | None = None
) -> Song | None:
    song = await get_song_by_id(session, song_id)
    if not song:
        return None
    if title is not None:
        song.title = title
    if lyrics is not None:
        song.lyrics = lyrics
    await session.commit()
    await session.refresh(song)
    return song


async def delete_song(session: AsyncSession, song_id: int) -> bool:
    song = await get_song_by_id(session, song_id)
    if not song:
        return False
    await session.delete(song)
    await session.commit()
    return True
