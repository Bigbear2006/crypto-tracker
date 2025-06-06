import asyncio

from asgiref.sync import sync_to_async

from bot.api.dexscreener import DexscreenerAPI
from bot.text_utils import chunk_list
from core.models import Coin


async def bulk_get_or_create_coins(
    chain: str,
    addresses: list[str],
) -> dict[str, Coin]:
    if len(addresses) > 30:
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(bulk_get_or_create_coins(chain, chunk))
                for chunk in chunk_list(addresses, 30)
            ],
        )
        return {k: v for i in done for k, v in i.result().items()}

    existed_coins = await sync_to_async(
        lambda: list(Coin.objects.filter(chain=chain, address__in=addresses)),
    )()

    async with DexscreenerAPI() as api:
        coins_info = await api.get_coins_info(chain, addresses)

    new_coins = [
        await Coin.objects.aget_or_create(info.address, chain, info)
        for info in coins_info
    ]

    coins = [*existed_coins, *new_coins]
    return {i.address: i for i in coins}
