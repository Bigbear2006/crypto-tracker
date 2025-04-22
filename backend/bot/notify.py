import asyncio
from collections.abc import Iterator
from itertools import groupby

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from asgiref.sync import sync_to_async
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import QuerySet

from bot.api.dexscreener import DexscreenerAPI
from bot.api.solana import SolanaAPI
from bot.loader import bot, logger, loop
from bot.schemas import CoinInfo, Transaction
from bot.settings import settings
from core.models import Client, Coin, CoinTrackingParams, TxHash, Wallet


def handle_send_message_errors(send_message_func):
    async def decorator(chat_id: str | int, text: str):
        try:
            await send_message_func(chat_id, text)
        except TelegramRetryAfter as e:
            logger.info(
                f'Cannot send a message to user (id={chat_id}) '
                f'because of rate limit',
            )
            await asyncio.sleep(e.retry_after)
            await send_message_func(chat_id, text)
        except TelegramBadRequest as e:
            logger.info(
                f'Cannot send a message to user (id={chat_id}) '
                f'because of {e.__class__.__name__} error: {str(e)}',
            )

    return decorator


@handle_send_message_errors
async def safe_send_message(chat_id: int | str, text: str):
    await bot.send_message(chat_id, text)


def chunk_list(lst: list, size: int) -> list:
    return [lst[i : i + size] for i in range(0, len(lst), size)]


async def send_coin_message(clients: QuerySet, coin_info: CoinInfo):
    text = (
        f'Монета {coin_info.symbol}\n'
        f'Изменение цены за 5 минут ({coin_info.price_5m_percents}%):\n'
        f'{coin_info.price_5m} -> {coin_info.price}'
    )

    await asyncio.wait(
        [
            asyncio.create_task(safe_send_message(c.pk, text))
            async for c in clients
        ],
    )


async def notify_coins_prices_changes():
    async def _notify(_api: DexscreenerAPI, addresses: list[str], chain: str):
        logger.info(
            f'Starting notify_coins_prices_changes '
            f'with {len(addresses)} addresses on chain {chain}...',
        )
        addresses = chunk_list(addresses, 30)
        await asyncio.wait(
            [
                asyncio.create_task(
                    send_coin_message(
                        Client.objects.filter(
                            coins__coin__address=coin.address,
                            coins__tracking_param=CoinTrackingParams.PRICE_UP
                            if coin.price_5m_percents > 0
                            else CoinTrackingParams.PRICE_DOWN,
                            coins__tracking_price__gte=abs(
                                float(coin.price) - float(coin.price_5m),
                            ),
                            notifications_enabled=True,
                        ),
                        coin,
                    ),
                )
                for addresses_chunk in addresses
                for coin in await _api.get_coins_info(chain, addresses_chunk)
                if coin.price_5m_percents is not None
            ],
        )

    async with DexscreenerAPI() as api:
        await asyncio.wait(
            [
                asyncio.create_task(_notify(api, **coin))
                async for coin in Coin.objects.values('chain').annotate(
                    addresses=ArrayAgg('address'),
                )
            ],
        )


async def get_wallet_new_transactions(
    api: SolanaAPI,
    wallet: Wallet,
) -> list[Transaction]:
    transactions = await api.get_signatures(wallet.address)
    already_sent_transactions = await sync_to_async(
        lambda: TxHash.objects.filter(
            tx_hash__in=transactions,
        ).values_list('tx_hash', flat=True),
    )()

    done, _ = await asyncio.wait(
        [
            asyncio.create_task(api.get_transaction(wallet.address, tx))
            for tx in transactions
            if tx not in already_sent_transactions
        ],
    )
    return [i.result() for i in done]


async def filter_wallet_transactions(
    api: DexscreenerAPI,
    token_address: str,
    tx_list: Iterator[Transaction],
) -> list[tuple[Transaction, CoinInfo]]:
    info = await api.get_coins_info('solana', [token_address])

    if not info:
        return []

    coin_info = info[0]
    return [
        (tx, coin_info)
        for tx in tx_list
        if (
            coin_info.price <= settings.MAX_COIN_PRICE
            and coin_info.market_cap >= settings.MIN_COIN_MARKET_CAP
            and tx.token_amount * coin_info.price >= settings.MIN_BUYING_AMOUNT
        )
    ]


async def send_wallet_transaction(tx: Transaction, coin_info: CoinInfo) -> str:
    text = (
        f'Кошелек {tx.wallet_address}\n\n'
        f'Покупка монеты {coin_info.symbol}\n'
        f'Цена монеты: {coin_info.price} (5м: {coin_info.price_5m}%) USD\n'
        f'Рыночная капитализация: {coin_info.market_cap} USD\n'
        f'Количество: {tx.token_amount}\n'
        f'Общая сумма: {tx.token_amount * coin_info.price} USD'
    )
    wallet = await Wallet.objects.aget(address=tx.wallet_address)
    await asyncio.wait(
        [
            asyncio.create_task(safe_send_message(c.pk, text))
            async for c in Client.objects.filter(
                wallets__wallet=wallet,
                notifications_enabled=True,
            )
        ],
    )
    return tx.signature


async def notify_wallets_transactions():
    logger.info('Starting notify_wallets_transactions...')
    async with SolanaAPI() as api:
        done, _ = await asyncio.wait(
            [
                asyncio.create_task(get_wallet_new_transactions(api, w))
                async for w in Wallet.objects.all()
            ],
        )
        transactions = [tx for i in done for tx in i.result()]

    async with DexscreenerAPI() as api:
        transactions = sorted(transactions, key=lambda t: t.address)
        done, _ = await asyncio.wait(
            [
                asyncio.create_task(
                    filter_wallet_transactions(api, address, tx_list),
                )
                for address, tx_list in groupby(
                    transactions,
                    lambda t: t.address,
                )
            ],
        )

    done, _ = await asyncio.wait(
        [
            asyncio.create_task(send_wallet_transaction(*i.result()))
            for i in done
        ],
    )

    await TxHash.objects.abulk_create(
        [TxHash(tx_hash=i.result()) for i in done],
    )


async def notify():
    await notify_coins_prices_changes()
    await asyncio.sleep(settings.NOTIFY_COINS_TIMEOUT)
    await notify_wallets_transactions()
    await asyncio.sleep(settings.NOTIFY_WALLETS_TIMEOUT)
    loop.create_task(notify())
