import asyncio
from dataclasses import asdict
from datetime import timedelta

from django.utils.timezone import now

from bot.api.base import APIClient
from bot.exceptions import CoinNotFound
from bot.loader import logger
from bot.schemas import (
    CoinHistory,
    CoinInputData,
    CoinPrice,
    HistoricalPrice,
    TransactionData,
)
from bot.settings import settings


class AlchemyAPI(APIClient):
    def __init__(self, **session_kwargs):
        super().__init__(**session_kwargs)

    async def get_signatures(
        self,
        address: str,
        *,
        limit: int = 10,
    ) -> list[str]:
        async with self.session.post(
            f'https://solana-mainnet.g.alchemy.com/v2/'
            f'{settings.ALCHEMY_API_KEY}/',
            json={
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'getSignaturesForAddress',
                'params': [
                    address,
                    {'limit': limit, 'commitment': 'confirmed'},
                ],
            },
        ) as rsp:
            data = await rsp.json()
            logger.debug(data)

            if rsp.status == 429:
                retry_after = int(rsp.headers.get('Retry-After', 10))
                logger.debug(f'Sleep {retry_after} seconds...')
                await asyncio.sleep(retry_after)
                await self.get_signatures(address, limit=limit)

            if err := data.get('error'):
                logger.info(f'Error {err}')
                return []

            return [i['signature'] for i in data['result']]

    async def get_transaction(
        self,
        wallet_address: str,
        signature: str,
    ) -> TransactionData | None:
        async with self.session.post(
            f'https://solana-mainnet.g.alchemy.com/v2/'
            f'{settings.ALCHEMY_API_KEY}/',
            json={
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'getTransaction',
                'params': [
                    signature,
                    {
                        'commitment': 'confirmed',
                        'maxSupportedTransactionVersion': 0,
                    },
                ],
            },
        ) as rsp:
            data = await rsp.json()

            if not data.get('result'):
                logger.info(data)
                return

            if err := data['result']['meta'].get('err'):
                logger.info(err)
                return

            # if signature == 'test_000':
            #     return TransactionData(
            #         wallet_address='HSYkA267XP4uiQjEcjAhbJfySvptQzRgBG3XPZpZJqxf',
            #         token_address='6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN',
            #         token_amount=12.56,
            #         timestamp=1746282199,
            #         signature='test_000',
            #     )

            if rsp.status == 429:
                retry_after = int(rsp.headers.get('Retry-After', 10))
                logger.debug(f'Sleep {retry_after} seconds...')
                await asyncio.sleep(retry_after)
                await self.get_transaction(wallet_address, signature)

            if err := data.get('error'):
                logger.info(f'Error {err}')
                return

            try:
                meta = data['result']['meta']
                pre_token_balance = [
                    i
                    for i in meta['preTokenBalances']
                    if i['owner'] == wallet_address
                ][0]

                post_token_balance = [
                    i
                    for i in meta['postTokenBalances']
                    if i['owner'] == wallet_address
                ][0]
            except IndexError:
                return

            token_amount = (
                post_token_balance['uiTokenAmount']['uiAmount'] or 0
            ) - (pre_token_balance['uiTokenAmount']['uiAmount'] or 0)

            return TransactionData(
                wallet_address=wallet_address,
                token_address=pre_token_balance['mint'],
                token_amount=token_amount,
                timestamp=data['result']['blockTime'],
                signature=signature,
            )

    async def get_historical_prices(
        self,
        chain: str,
        address: str,
    ) -> CoinHistory | None:
        date = now()
        async with self.session.post(
            f'https://api.g.alchemy.com/prices/v1/'
            f'{settings.ALCHEMY_API_KEY}/tokens/historical',
            json={
                'startTime': (date - timedelta(minutes=30)).isoformat(),
                'endTime': date.isoformat(),
                'interval': '5m',
                'withMarketData': True,
                'network': chain,
                'address': address,
            },
        ) as rsp:
            data = await rsp.json()
            logger.debug(data)

        if err := data.get('error'):
            logger.info(err)
            return

        return CoinHistory(
            address=data['address'],
            chain=data['network'],
            prices=[
                HistoricalPrice(
                    price=i['value'],
                    timestamp=i['timestamp'],
                    market_cap=i['marketCap'],
                )
                for i in data['data']
            ],
        )

    async def get_coins_prices(
        self,
        addresses: list[CoinInputData],
    ) -> list[CoinPrice]:
        async with self.session.post(
            f'https://api.g.alchemy.com/prices/v1/'
            f'{settings.ALCHEMY_API_KEY}/tokens/by-address',
            json={'addresses': [asdict(i) for i in addresses]},
        ) as rsp:
            data = await rsp.json()
            logger.debug(data)

        return [
            CoinPrice(
                address=i['address'],
                chain=i['network'],
                price=i['prices'][0]['value'],
            )
            for i in data['data']
            if i.get('prices')
        ]

    async def get_coin_price(self, chain: str, address: str) -> CoinPrice:
        coins = await self.get_coins_prices([CoinInputData(chain, address)])
        if not coins:
            raise CoinNotFound(address=address)
        return coins[0]


alchemy_chains = {
    'solana': 'solana-mainnet',
    'ethereum': 'eth-mainnet',
    'base': 'base-mainnet',
    'blast': 'blast-mainnet',
}
