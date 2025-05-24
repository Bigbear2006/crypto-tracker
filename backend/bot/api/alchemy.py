from dataclasses import asdict
from datetime import timedelta

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
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

alchemy_chains = {
    'solana': 'solana-mainnet',
    'ethereum': 'eth-mainnet',
    'base': 'base-mainnet',
    'blast': 'blast-mainnet',
}


class AlchemyAPI(APIClient):
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

            if err := data.get('error'):
                logger.info(f'Error {err}')
                return

            meta = data['result']['meta']
            token_address = token_address_from_meta(meta)
            balance_change = get_token_balance_change(meta, wallet_address)

            if balance_change is None:
                Coin = apps.get_model('core', 'Coin')
                try:
                    coin = await Coin.objects.aget_or_create(
                        token_address,
                        'solana',
                    )
                    balance_change = get_token_balance_change(
                        meta,
                        coin.pair_address,
                    )
                except (ObjectDoesNotExist, CoinNotFound):
                    logger.info(f'Coin {token_address} not found')
                    return

            if balance_change is None:
                logger.info(
                    f'[attempt 2] Cannot get balance change '
                    f'in transaction {signature}',
                )

                for i in meta['preTokenBalances']:
                    balance_change = get_token_balance_change(meta, i['owner'])
                    if balance_change:
                        balance_change = abs(balance_change)
                        break

            if balance_change is None:
                logger.info(
                    f'[attempt 3] Cannot get balance change '
                    f'in transaction {signature}',
                )
                return

            return TransactionData(
                wallet_address=wallet_address,
                token_address=token_address,
                token_amount=balance_change,
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

        if not data.get('data'):
            logger.info(data)
            return []

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


def get_token_balance_change(meta: dict, owner: str) -> float | None:
    try:
        pre_token_balance = [
            i
            for i in meta['preTokenBalances']
            if i['owner'] == owner
            if i['mint'] != settings.WSOL_ADDRESS
        ][0]

        post_token_balance = [
            i
            for i in meta['postTokenBalances']
            if i['owner'] == owner
            if i['mint'] != settings.WSOL_ADDRESS
        ][0]

        return (pre_token_balance['uiTokenAmount']['uiAmount'] or 0) - (
            post_token_balance['uiTokenAmount']['uiAmount'] or 0
        )
    except IndexError:
        return


def token_address_from_meta(meta: dict) -> str | None:
    addresses = [
        i['mint']
        for i in meta['preTokenBalances']
        if i['mint'] != settings.WSOL_ADDRESS
    ]
    if addresses:
        return addresses[0]
