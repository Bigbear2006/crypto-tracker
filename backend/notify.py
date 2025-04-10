import asyncio
import os

import cfscrape
import cloudscraper
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from bot import gmgn
from bot.loader import bot, logger
from bot.settings import settings
from core.models import Wallet, Client

task_logger = logger


def handle_send_message_errors(send_message_func):
    async def decorator(chat_id: str | int):
        try:
            await send_message_func(chat_id)
        except TelegramRetryAfter as e:
            task_logger.info(
                f'Cannot send a message to user (id={chat_id}) '
                f'because of rate limit',
            )
            await asyncio.sleep(e.retry_after)
            await send_message_func(chat_id)
        except TelegramBadRequest as e:
            task_logger.info(
                f'Cannot send a message to user (id={chat_id}) '
                f'because of {e.__class__.__name__} error: {str(e)}',
            )

    return decorator


async def notify():
    async def _notify(_wallet: Wallet):
        @handle_send_message_errors
        async def __notify(_client: Client):
            await bot.send_message(_client.pk, msg_text)

        activities = [
            a
            for a in await gmgn.get_wallet_activity(_wallet.address, 'sol')
            if a.cost_usd >= settings.MIN_BUYING_AMOUNT
            and a.price_usd <= settings.MAX_COIN_PRICE
        ]
        msg_text = f'Кошелёк {_wallet.address}' + '\n\n'.join(
            [a.to_text() for a in activities]
        )

        await asyncio.wait(
            [
                asyncio.create_task(__notify(c))
                async for c in Client.objects.filter(
                    wallets__wallet=_wallet.address
                )
            ]
        )

    await asyncio.wait(
        [asyncio.create_task(_notify(w)) async for w in Wallet.objects.all()]
    )


if __name__ == '__main__':
    asyncio.run(notify())
