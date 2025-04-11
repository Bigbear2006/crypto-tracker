import random
import string

from aiohttp import ClientSession

from bot.loader import logger
from bot.schemas import BaseCoinInfo, CoinInfo, CoinPrice, WalletActivity
from bot.settings import settings


def get_headers():
    return {
        'Cookie': settings.GMGN_COOKIE,
        'Origin': 'https://gmgn.ai',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/135.0.0.0 Safari/537.36',
    }


async def __get_coin_info(address: str) -> CoinInfo:
    name = ''.join(random.choices(string.ascii_lowercase, k=5))
    return CoinInfo(address, name.upper(), '', name.title())


async def get_coins_info(addresses: list[str], chain: str) -> list[CoinInfo]:
    data = {
        'chain': chain,
        'addresses': addresses,
    }
    async with ClientSession(settings.GMGN_API_URL) as session:
        async with session.post(
            'mutil_window_token_info',
            headers=get_headers(),
            json=data,
        ) as rsp:
            data = await rsp.json()
            if data['data'] is None:
                logger.info(f'Response<{rsp.status}> data is null: {data}')
                return []
            return [
                CoinInfo(i['address'], i['symbol'], i['logo'], i['name'])
                for i in data['data']
            ]


async def get_coin_info(address: str, chain: str) -> CoinInfo:
    return (await get_coins_info([address], chain))[0]


async def get_wallet_activity(
    address: str,
    chain: str,
) -> list[WalletActivity]:
    params = {
        'wallet': address,
    }
    async with ClientSession(settings.GMGN_API_URL) as session:
        async with session.get(
            f'wallet_activity/{chain}',
            headers=get_headers(),
            params=params,
        ) as rsp:
            data = await rsp.json()
            return [
                WalletActivity(
                    i['event_type'],
                    i['cost_usd'],
                    i['price_usd'],
                    BaseCoinInfo(**i['token']),
                    i['token_amount'],
                    i['timestamp'],
                    i['tx_hash'],
                )
                for i in data['data']['activities']
            ]


async def get_coins_prices(
    addresses: list[str],
    chain: str,
) -> list[CoinPrice]:
    data = {
        'chain': chain,
        'addresses': addresses,
    }
    async with ClientSession(settings.GMGN_API_URL) as session:
        async with session.post(
            'mutil_window_token_info',
            headers=get_headers(),
            json=data,
        ) as rsp:
            data = await rsp.json()
            return [
                CoinPrice(
                    i['address'],
                    i['price']['price'],
                    i['price']['price_1m'],
                )
                for i in data['data']
            ]
