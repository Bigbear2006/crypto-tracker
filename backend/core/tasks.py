import asyncio

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from asgiref.sync import sync_to_async
from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import QuerySet, Count

from bot import gmgn
from bot.loader import bot
from bot.schemas import CoinPrice, EventType
from bot.settings import settings
from core.models import Client, Coin, CoinTrackingParams, Wallet, TxHash

task_logger = get_task_logger(__name__)


@shared_task
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


def chunk_list(lst: list, size: int) -> list:
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def notify_wallet_buying():
    async def _notify(_wallet: Wallet):
        activities = [
            activity
            for activity in await gmgn.get_wallet_activity(
                _wallet.address,
                _wallet.chain,
            )
            if float(activity.cost_usd) >= settings.MIN_BUYING_AMOUNT
            and float(activity.price_usd) <= settings.MAX_COIN_PRICE
            and activity.event_type == EventType.buy
        ]

        already_sent_activities = sync_to_async(list)(
            TxHash.objects.filter(
                tx_hash__in=[a.tx_hash for a in activities]
            ).values_list('tx_hash', flat=True)
        )

        activities = [
            activity
            for activity in activities
            if activity.tx_hash not in already_sent_activities
        ]

        coins_with_sufficient_mkt_cap = [
            coin
            for coin in await gmgn.get_coins_mkt_cap(
                list({activity.token.address for activity in activities}),
                _wallet.chain,
            )
            if coin.mkt_cap > settings.MIN_COIN_MKT_CAP
        ]

        activities = [
            activity
            for activity in activities
            if activity.token.address in coins_with_sufficient_mkt_cap
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

        await TxHash.objects.abulk_create([TxHash(tx_hash=activity.tx_hash) for activity in activities])

    async def main():
        await asyncio.wait(
            [
                asyncio.create_task(_notify(w))
                async for w in Wallet.objects.all()
            ],
        )

    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
    loop.run_until_complete(main())


@shared_task
def notify_coin_price_changes():
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

        addresses = chunk_list(addresses, 10)
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
                for addresses_chunk in addresses
                for price in await gmgn.get_coins_prices(addresses_chunk, chain)
            ],
        )

    async def main():
        await asyncio.wait(
            [
                asyncio.create_task(_notify(**coin))
                async for coin in Coin.objects.values('chain').annotate(
                    addresses=ArrayAgg('address'),
                )
            ],
        )

    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
