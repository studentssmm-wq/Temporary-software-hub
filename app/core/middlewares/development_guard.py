"""Keep development Telegram traffic inside private chats that interacted with this test bot."""
from aiogram import BaseMiddleware
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.exceptions import TelegramBadRequest

class DevelopmentUpdateGuard(BaseMiddleware):
    def __init__(self,recipients):
        self.recipients=recipients
    async def __call__(self,handler,event,data):
        message=event.message
        if message is None and event.callback_query:
            message=event.callback_query.message
        if message is not None:
            if message.chat.type!="private":
                return None
            self.recipients.add(message.chat.id)
        return await handler(event,data)

class DevelopmentRequestGuard(BaseRequestMiddleware):
    def __init__(self,recipients):
        self.recipients=recipients
    async def __call__(self,make_request,bot,method):
        chat_id=getattr(method,"chat_id",None)
        if chat_id is not None and chat_id not in self.recipients:
            raise TelegramBadRequest(method=method,message="Development recipient has not interacted with this test bot")
        return await make_request(bot,method)
