import json
import random
import string

from aiohttp import ClientSession

from bot.loader import logger
from bot.schemas import CoinInfo
from bot.settings import settings


def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/134.0.0.0 Safari/537.36',
        'Cookie': '',
    }


async def get_coin_info(address: str) -> CoinInfo:
    # 7tJCkYgtmq73WvvCYx8BfZAbCCzv25gFvRZr2TQdpNbF
    # EQ8XnCvwZvhdJZZZeJeRv5bYyNTz5vQ4TL9VFxwCPcZc - no symbol
    name = ''.join(random.choices(string.ascii_lowercase, k=5))
    return CoinInfo(address, name.upper(), name.title(), '')


async def _get_coin_info(address: str) -> CoinInfo:
    data = {
        'chain': 'sol',
        'addresses': [address],
    }
    async with ClientSession(settings.GMGN_API_URL) as session:
        async with session.post(
            'mutil_window_token_info',
            headers=get_headers(),
            json=data,
        ) as rsp:
            data = await rsp.json()
            logger.info(json.dumps(data, indent=4))
            return CoinInfo(**data['data'][0])


async def wallet():
    params = {
        'wallet': '71CPXu3TvH3iUKaY1bNkAAow24k6tjH473SsKprQBABC',
    }
    async with ClientSession(settings.GMGN_API_URL) as session:
        async with session.get(
            'wallet_activity/sol',
            headers=get_headers(),
            params=params,
        ) as rsp:
            data = await rsp.json()
            logger.info(json.dumps(data, indent=4))
            return data['data'][0]
