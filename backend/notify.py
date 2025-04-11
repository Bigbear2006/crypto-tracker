import asyncio
import os

import django
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import QuerySet

from bot import gmgn
from bot.loader import bot, logger
from bot.schemas import CoinPrice
from bot.settings import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Client, Coin, CoinTrackingParams, Wallet  # noqa

task_logger = logger


def handle_send_message_errors(send_message_func):
    async def decorator(chat_id: str | int, text: str):
        try:
            await send_message_func(chat_id, text)
        except TelegramRetryAfter as e:
            task_logger.info(
                f'Cannot send a message to user (id={chat_id}) '
                f'because of rate limit',
            )
            await asyncio.sleep(e.retry_after)
            await send_message_func(chat_id, text)
        except TelegramBadRequest as e:
            task_logger.info(
                f'Cannot send a message to user (id={chat_id}) '
                f'because of {e.__class__.__name__} error: {str(e)}',
            )

    return decorator


@handle_send_message_errors
async def safe_send_message(chat_id: int | str, text: str):
    await bot.send_message(chat_id, text)


async def notify_wallet_buying():
    async def _notify(_wallet: Wallet):
        activities = [
            activity
            for activity in await gmgn.get_wallet_activity(
                _wallet.address,
                _wallet.chain,
            )
            if float(activity.cost_usd) >= settings.MIN_BUYING_AMOUNT
            and float(activity.price_usd) <= settings.MAX_COIN_PRICE
            and activity.event_type == 'buy'
        ]

        msg_text = f'Кошелёк {_wallet.address}\n\n' + '\n\n'.join(
            [a.to_text() for a in activities],
        )

        await asyncio.wait(
            [
                asyncio.create_task(safe_send_message(c.pk, msg_text))
                async for c in Client.objects.filter(wallets__wallet=_wallet)
            ],
        )

    await asyncio.wait(
        [asyncio.create_task(_notify(w)) async for w in Wallet.objects.all()],
    )


async def notify_coin_price_changes():
    async def _notify(addresses: list[str], chain: str):
        async def __notify(_clients: QuerySet, _coin: Coin, _price: CoinPrice):
            msg_text = (
                f'Монета {_coin}\nЦена сейчас: {_price.price}\n'
                f'Цена минуту назад: {_price.price_1m}'
            )

            await asyncio.wait(
                [
                    asyncio.create_task(safe_send_message(c.pk, msg_text))
                    async for c in _clients
                ],
            )

        await asyncio.wait(
            [
                asyncio.create_task(
                    __notify(
                        Client.objects.filter(
                            coins__coin__address=price.address,
                            coins__tracking_param=CoinTrackingParams.PRICE_UP
                            if price.price > price.price_1m
                            else CoinTrackingParams.PRICE_DOWN,
                            coins__tracking_price__gte=abs(
                                float(price.price) - float(price.price_1m),
                            ),
                        ),
                        await Coin.objects.aget(address=price.address),
                        price,
                    ),
                )
                for price in await gmgn.get_coins_prices(addresses, chain)
            ],
        )

    await asyncio.wait(
        [
            asyncio.create_task(_notify(**coin))
            async for coin in Coin.objects.values('chain').annotate(
                addresses=ArrayAgg('address'),
            )
        ],
    )


if __name__ == '__main__':
    asyncio.run(notify_wallet_buying())
