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
            (
                client,
                created,
            ) = await Client.objects.create_or_update_from_tg_user(
                event.from_user,
            )
            data['client'] = client
            data['client_created'] = created
        return await handler(event, data)
