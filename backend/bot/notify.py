import asyncio
from asyncio import ALL_COMPLETED
from datetime import UTC, datetime
from itertools import groupby

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from asgiref.sync import sync_to_async
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q

from bot.api.alchemy import AlchemyAPI
from bot.exceptions import CoinNotFound
from bot.loader import bot, logger, loop
from bot.schemas import CoinHistory, CoinInputData, CoinPrice, TransactionData
from bot.settings import settings
from core.models import (
    Client,
    ClientCoin,
    Coin,
    CoinTrackingParams,
    Transaction,
    Wallet,
)


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


async def asyncio_wait(
    fs,
    *,
    timeout=None,
    return_when=ALL_COMPLETED,
) -> tuple[set, set]:
    if not fs:
        return set(), set()
    return await asyncio.wait(fs, timeout=timeout, return_when=return_when)


async def send_coin_message(coin_price: CoinPrice):
    coin = await Coin.objects.aget(
        address=coin_price.address,
        chain=coin_price.chain,
    )

    clients = Client.objects.filter(
        Q(
            coins__tracking_param=CoinTrackingParams.PRICE_UP,
            coins__tracking_price__gte=coin_price.price,
        )
        | Q(
            coins__tracking_param=CoinTrackingParams.PRICE_DOWN,
            coins__tracking_price__lte=coin_price.price,
        ),
        coins__coin__address=coin_price.address,
        coins__notification_sent=False,
        alerts_enabled=True,
    )

    text = f'Цена монеты {coin.symbol} достигла {coin_price.price}$'
    await asyncio_wait(
        [
            asyncio.create_task(safe_send_message(c.pk, text))
            async for c in clients
        ],
    )

    await ClientCoin.objects.filter(client__in=clients).aupdate(
        notification_sent=True,
    )


async def notify_coins_prices_changes():
    async def _notify(_api: AlchemyAPI, addresses: list[str], chain: str):
        logger.info(
            f'Starting notify_coins_prices_changes '
            f'with {len(addresses)} addresses on chain {chain}...',
        )

        addresses = chunk_list(addresses, 25)
        await asyncio_wait(
            [
                asyncio.create_task(send_coin_message(coin_price))
                for addresses_chunk in addresses
                for coin_price in await _api.get_coins_prices(
                    CoinInputData.from_network(chain, addresses_chunk),
                )
            ],
        )

    async with AlchemyAPI() as api:
        await asyncio_wait(
            [
                asyncio.create_task(_notify(api, **coin))
                async for coin in Coin.objects.values('chain').annotate(
                    addresses=ArrayAgg('address'),
                )
            ],
        )


async def get_wallet_new_transactions(
    api: AlchemyAPI,
    wallet: Wallet,
) -> list[TransactionData]:
    transactions = await api.get_signatures(wallet.address)

    # if wallet.address == 'HSYkA267XP4uiQjEcjAhbJfySvptQzRgBG3XPZpZJqxf':
    #     transactions = ['test_000']

    already_sent_transactions = await sync_to_async(
        lambda: list(
            Transaction.objects.filter(signature__in=transactions).values_list(
                'signature',
                flat=True,
            ),
        ),
    )()

    done, _ = await asyncio_wait(
        [
            asyncio.create_task(api.get_transaction(wallet.address, tx))
            for tx in transactions
            if tx not in already_sent_transactions
        ],
    )
    return [i.result() for i in done]


async def filter_wallet_transactions(
    api: AlchemyAPI,
    token_address: str,
    tx_list: list[TransactionData],
) -> list[tuple[TransactionData, Coin, CoinHistory]]:
    prices = await api.get_historical_prices('solana-mainnet', token_address)

    if not prices:
        return []

    try:
        coin = await Coin.objects.aget_or_create(token_address, 'solana')
    except CoinNotFound:
        return []

    await Transaction.objects.abulk_create(
        [
            Transaction(
                wallet=await Wallet.objects.aget(address=tx.wallet_address),
                coin=coin,
                coin_amount=tx.token_amount,
                coin_price=prices.price,
                total_cost=tx.token_amount * prices.price,
                date=datetime.fromtimestamp(tx.timestamp, tz=UTC),
                signature=tx.signature,
            )
            for tx in tx_list
        ],
    )

    return [
        (tx, coin, prices)
        for tx in tx_list
        if (
            prices.price <= settings.MAX_COIN_PRICE
            and prices.market_cap >= settings.MIN_COIN_MARKET_CAP
            and tx.token_amount * prices.price >= settings.MIN_BUYING_AMOUNT
        )
    ]


async def send_wallet_transaction(
    tx: TransactionData,
    coin: Coin,
    history: CoinHistory,
) -> str:
    text = (
        f'Кошелек {tx.wallet_address}\n\n'
        f'Покупка монеты {coin.symbol}\n'
        f'Цена монеты: {history.price} USD\n'
        f'Рыночная капитализация: {history.market_cap} USD\n'
        f'Количество: {tx.token_amount}\n'
        f'Общая сумма: {tx.token_amount * history.price} USD'
    )
    wallet = await Wallet.objects.aget(address=tx.wallet_address)
    await asyncio_wait(
        [
            asyncio.create_task(safe_send_message(c.pk, text))
            async for c in Client.objects.filter(
                wallets__wallet=wallet,
                alerts_enabled=True,
            )
        ],
    )
    return tx.signature


async def notify_wallets_transactions():
    logger.info('Starting notify_wallets_transactions...')
    async with AlchemyAPI() as api:
        done, _ = await asyncio_wait(
            [
                asyncio.create_task(get_wallet_new_transactions(api, w))
                async for w in Wallet.objects.all()
            ],
        )
        transactions = [
            tx for i in done for tx in i.result() if tx is not None
        ]

    async with AlchemyAPI() as api:
        transactions = sorted(transactions, key=lambda t: t.token_address)
        done, _ = await asyncio_wait(
            [
                asyncio.create_task(
                    filter_wallet_transactions(api, address, list(tx_list)),
                )
                for address, tx_list in groupby(
                    transactions,
                    lambda t: t.token_address,
                )
            ],
        )
        done = [j for i in done for j in i.result()]

    if done:
        done, _ = await asyncio_wait(
            [asyncio.create_task(send_wallet_transaction(*i)) for i in done],
        )
        await Transaction.objects.filter(
            signature__in=[i.result() for i in done],
        ).aupdate(sent=True)
    else:
        logger.info('There are no new transactions')


async def notify():
    await notify_coins_prices_changes()
    await asyncio.sleep(settings.NOTIFY_COINS_TIMEOUT)
    await notify_wallets_transactions()
    await asyncio.sleep(settings.NOTIFY_WALLETS_TIMEOUT)
    loop.create_task(notify())
