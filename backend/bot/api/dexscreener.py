from datetime import UTC, datetime

from aiohttp import ContentTypeError

from bot.api.base import APIClient
from bot.exceptions import CoinNotFound
from bot.loader import logger
from bot.schemas import CoinInfo


class DexscreenerAPI(APIClient):
    def __init__(self, **session_kwargs):
        super().__init__(
            'https://api.dexscreener.com/',
            **session_kwargs,
        )

    async def get_coins_info(
        self,
        chain: str,
        addresses: list[str],
    ) -> list[CoinInfo]:
        async with self.session.get(
            f'tokens/v1/{chain}/{",".join(addresses)}',
        ) as rsp:
            try:
                data = await rsp.json()
            except ContentTypeError:
                logger.info(
                    f'get_coins_info(chain={chain}, addresses={addresses[:2]})'
                    f' returns text: {await rsp.text()}',
                )
                return []

        return [
            CoinInfo(
                address=i['baseToken']['address'],
                symbol=i['baseToken']['symbol'],
                logo=i.get('info', {}).get('imageUrl', ''),
                name=i['baseToken']['name'],
                pair_address=i['pairAddress'],
                created_at=datetime.fromtimestamp(
                    i['pairCreatedAt'] / 1000,
                    tz=UTC,
                ),
                market_cap=i['marketCap'],
                price=i['priceUsd'],
                price_5m_percents=i['priceChange'].get('price_m5'),
            )
            for i in data
            if i.get('marketCap')
            if i.get('pairCreatedAt')
        ]

    async def get_coin_info(self, chain: str, address: str):
        coins = await self.get_coins_info(chain, [address])
        if not coins:
            raise CoinNotFound(address=address)
        return coins[0]
