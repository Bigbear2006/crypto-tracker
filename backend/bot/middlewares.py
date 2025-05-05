from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import Message, TelegramObject

from core.models import Client


class WithClientMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        with_client = get_flag(data, 'with_client')
        if with_client:
            pk = (
                event.chat.id
                if isinstance(event, Message)
                else event.message.chat.id
            )
            client = await Client.objects.aget(pk=pk)
            data['client'] = client
        return await handler(event, data)
