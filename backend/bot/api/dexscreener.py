from aiohttp import ClientSession

from bot.exceptions import CoinNotFound
from bot.loader import logger
from bot.schemas import CoinInfo


class DexscreenerAPI:
    def __init__(self, **session_kwargs):
        self.session = ClientSession(
            'https://api.dexscreener.com/',
            **session_kwargs,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def get_coins_info(
        self,
        chain: str,
        addresses: list[str],
    ) -> list[CoinInfo]:
        async with self.session.get(
            f'tokens/v1/{chain}/{",".join(addresses)}',
        ) as rsp:
            data = await rsp.json()
            logger.debug(data)
            return [
                CoinInfo(
                    address=i['baseToken']['address'],
                    symbol=i['baseToken']['symbol'],
                    logo=i.get('info', {}).get('imageUrl', ''),
                    name=i['baseToken']['name'],
                    market_cap=i['marketCap'],
                    price=i['priceUsd'],
                    price_5m_percents=i['priceChange'].get('price_m5'),
                )
                for i in data
            ]

    async def get_coin_info(self, chain: str, address: str):
        coins = await self.get_coins_info(chain, [address])
        if not coins:
            raise CoinNotFound(address=address)
        return coins[0]
