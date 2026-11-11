"""Dependencies injected by the shared bot startup; no token or second dispatcher."""
from sqlalchemy import select
from app.core.config import ADMIN_IDS as CONFIG_ADMIN_IDS
from app.core.models import User
from app.features.ticketing.repository import TicketRepository

class BotProxy:
    _bot = None
    def configure(self, bot):
        self._bot = bot
    def __getattr__(self, name):
        if self._bot is None:
            raise RuntimeError("Ticket module has not been configured")
        return getattr(self._bot, name)

bot = BotProxy()
db = TicketRepository()
ADMIN_IDS = set(CONFIG_ADMIN_IDS)
BLACKLIST_CACHE = set()

async def configure_ticketing(shared_bot, session_factory):
    bot.configure(shared_bot)
    async with session_factory() as session:
        ADMIN_IDS.update((await session.execute(select(User.telegram_id).where(User.user_role == "admin"))).scalars())
    BLACKLIST_CACHE.update(name.lower() for name in await db.get_blacklist())


async def get_admin_ids():
    rows=await db.pool.fetch("SELECT telegram_id FROM users WHERE user_role='admin'")
    current=set(CONFIG_ADMIN_IDS)|{row["telegram_id"] for row in rows}
    ADMIN_IDS.clear()
    ADMIN_IDS.update(current)
    return current
