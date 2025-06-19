import asyncio
import time
from asyncio import ALL_COMPLETED
from collections.abc import Callable, Coroutine
from dataclasses import asdict
from datetime import UTC, datetime
from itertools import groupby
from typing import Any

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from asgiref.sync import sync_to_async
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import ExpressionWrapper, F, FloatField, Q

from bot.api.alchemy import AlchemyAPI
from bot.api.birdeye import BirdEyeAPI
from bot.api.dexscreener import DexscreenerAPI
from bot.exceptions import BirdEyeBadRequest, CoinNotFound
from bot.loader import bot, logger, loop
from bot.schemas import (
    CoinHistory,
    CoinInputData,
    CoinPrice,
    HistoricalPrice,
    TokenListParams,
    TransactionData,
)
from bot.services.client_filters import (
    filter_results,
    get_and_filter_results,
)
from bot.settings import settings
from bot.text_utils import chunk_list
from core.models import (
    Client,
    ClientCoin,
    ClientFilters,
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
            coins__percentage__lte=ExpressionWrapper(
                (coin_price.price - F('coins__start_price'))
                / F('coins__start_price')
                * 100,
                output_field=FloatField(),
            ),
        )
        | Q(
            coins__tracking_param=CoinTrackingParams.PRICE_DOWN,
            coins__percentage__gte=ExpressionWrapper(
                (F('coins__start_price') - coin_price.price)
                / F('coins__start_price')
                * 100,
                output_field=FloatField(),
            ),
        ),
        coins__coin__address=coin_price.address,
        coins__notification_sent=False,
        alerts_enabled=True,
    )

    text = f'Цена монеты {coin.symbol} достигла ${coin_price.price}'
    await asyncio_wait(
        [
            asyncio.create_task(safe_send_message(c.pk, text))
            async for c in clients
        ],
    )

    await ClientCoin.objects.filter(client__in=clients, coin=coin).aupdate(
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
                async for coin in Coin.objects.filter(
                    clients__isnull=False,
                    clients__client__alerts_enabled=True,
                )
                .values('chain')
                .annotate(addresses=ArrayAgg('address', distinct=True))
            ],
        )


async def get_wallet_new_transactions(
    api: AlchemyAPI,
    wallet: Wallet,
) -> list[TransactionData]:
    async def get_transaction(_tx: str):
        tr = await api.get_transaction(wallet.address, _tx)
        if not tr:
            await Transaction.objects.acreate(wallet=wallet, signature=_tx)
        return tr

    transactions = await api.get_signatures(wallet.address)
    already_sent_transactions = await sync_to_async(
        lambda: list(
            Transaction.objects.filter(
                wallet=wallet,
                signature__in=transactions,
            )
            .order_by('-date')
            .values_list('signature', flat=True)[:20],
        ),
    )()

    done, _ = await asyncio_wait(
        [
            asyncio.create_task(get_transaction(tx))
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
        async with DexscreenerAPI() as dex_api:
            try:
                coin_price = await api.get_coin_price(
                    'solana-mainnet',
                    token_address,
                )
                coin_info = await dex_api.get_coin_info(
                    'solana',
                    token_address,
                )
                prices = CoinHistory(
                    token_address,
                    'solana-mainnet',
                    [
                        HistoricalPrice(
                            price=str(coin_price.price),
                            timestamp=str(time.time()),
                            market_cap=coin_info.market_cap,
                        ),
                    ],
                )
                logger.info(prices)
            except CoinNotFound:
                await Transaction.objects.abulk_create(
                    [
                        Transaction(
                            wallet=await Wallet.objects.aget(
                                address=tx.wallet_address,
                            ),
                            coin_amount=tx.token_amount,
                            date=datetime.fromtimestamp(tx.timestamp, tz=UTC),
                            signature=tx.signature,
                        )
                        for tx in tx_list
                    ],
                )
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

    return [(tx, coin, prices) for tx in tx_list if tx.token_amount >= 0]


async def send_wallet_transaction(
    tx: TransactionData,
    coin: Coin,
    history: CoinHistory,
) -> str:
    text = (
        f'Кошелек {tx.wallet_address}\n\n'
        f'Покупка монеты {coin.symbol}\n'
        f'Цена монеты: ${history.price}\n'
        f'Рыночная капитализация: ${history.market_cap}\n'
        f'Количество: {tx.token_amount}\n'
        f'Общая сумма: ${tx.token_amount * history.price}'
    )
    wallet = await Wallet.objects.aget(address=tx.wallet_address)
    coin_age = (datetime.now(UTC) - coin.created_at).total_seconds() // 60
    await asyncio_wait(
        [
            asyncio.create_task(safe_send_message(c.pk, text))
            async for c in Client.objects.filter(
                Q(max_coin_price__gte=history.price)
                | Q(max_coin_price__isnull=True),
                Q(min_coin_market_cap__lte=history.market_cap)
                | Q(min_coin_market_cap__isnull=True),
                Q(min_coin_age__lte=coin_age) | Q(min_coin_age__isnull=True),
                Q(max_coin_age__gte=coin_age) | Q(max_coin_age__isnull=True),
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
                async for w in Wallet.objects.get_tracked()
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


async def get_new_coins(api: BirdEyeAPI, f: ClientFilters):
    results = filter_results(f, return_str=False)

    try:
        new_results = await get_and_filter_results(
            api,
            f,
            TokenListParams(
                min_liquidity=int(f.min_liquidity),
                offset=f.offset,
            ),
        )
    except BirdEyeBadRequest:
        # if offset is too large
        logger.info(f'Set offset=0 to ClientFilters {f}')
        await ClientFilters.objects.update_by_id(f.pk, offset=0)
        return

    data = {'offset': f.offset + 50}
    new_coins = [i for i in new_results if i not in results]
    if new_coins:
        text = '\n\n'.join(i.message_text for i in new_coins)
        await safe_send_message(
            f.client_id,
            f'Новые монеты по фильтрам:\n\n{text}'[:4000],
        )
        data['results'] = [*f.results, *[asdict(i) for i in new_coins]]

    await ClientFilters.objects.update_by_id(f.pk, **data)


async def notify_search_filters():
    async with BirdEyeAPI() as api:
        await asyncio_wait(
            [
                asyncio.create_task(get_new_coins(api, i))
                async for i in ClientFilters.objects.select_related(
                    'client',
                ).all()
            ],
        )


async def run_loop_task(
    func: Callable[[], Coroutine[Any, Any, None]],
    *,
    timeout: int = settings.NOTIFY_TIMEOUT,
):
    try:
        await func()
        await asyncio.sleep(timeout)
    except Exception as e:
        logger.exception(f'Error in {func.__name__}', exc_info=e)
        await asyncio.sleep(timeout)
    finally:
        loop.create_task(run_loop_task(func, timeout=timeout))


async def notify_coins():
    await run_loop_task(notify_coins_prices_changes)


async def notify_wallets():
    await run_loop_task(notify_wallets_transactions)


async def notify_filters():
    await run_loop_task(notify_search_filters, timeout=60)
