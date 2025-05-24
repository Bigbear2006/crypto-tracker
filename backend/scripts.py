import asyncio
import os

import django
from asgiref.sync import sync_to_async

from bot.loader import logger

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from bot.api.dexscreener import DexscreenerAPI  # noqa
from bot.notify import chunk_list  # noqa
from core.models import Coin  # noqa


async def update_coins_tokens_pairs():
    async def update_chunk(_api: DexscreenerAPI, _coins: list[Coin]):
        addresses = [i.address for i in _coins]
        coins_info = await api.get_coins_info('solana', addresses)
        coins_info_dict = {i.address: i for i in coins_info}

        for coin in _coins:
            coin_info = coins_info_dict.get(coin.address)
            if not coin_info:
                logger.info(
                    f'Coin {coin.address} does not exist on chain solana',
                )
                continue
            coin.pair_address = coin_info.pair_address

        await Coin.objects.abulk_update(_coins, ['pair_address'])

    logger.info('Starting update_coins_tokens_pairs...')
    coins_addresses = await sync_to_async(
        lambda: list(Coin.objects.all()),
    )()

    async with DexscreenerAPI() as api:
        await asyncio.wait(
            [
                asyncio.create_task(update_chunk(api, coins_chunk))
                for coins_chunk in chunk_list(coins_addresses, 30)
            ],
        )
    logger.info('update_coins_tokens_pairs completed!')


if __name__ == '__main__':
    asyncio.run(update_coins_tokens_pairs())
