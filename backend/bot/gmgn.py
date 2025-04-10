import random
import string

from aiohttp import ClientSession

from bot.loader import logger
from bot.schemas import CoinInfo, WalletActivity, BaseCoinInfo
from bot.settings import settings


def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/134.0.0.0 Safari/537.36',
        # 'Cookie': settings.GMGN_COOKIE,
        # 'Referer': 'https://gmgn.ai/api/v1/wallet_activity/sol?type=buy&type=sell&device_id=ea3e2ec0-141d-48cd-9781-c8dc393ff61d&client_id=gmgn_web_2025.0409.202756&from_app=gmgn&app_ver=2025.0409.202756&tz_name=Europe%2FMoscow&tz_offset=10800&app_lang=en-US&fp_did=6ffb17527a5ebe37751e83b869592461&os=web&wallet=71CPXu3TvH3iUKaY1bNkAAow24k6tjH473SsKprQBABC&limit=10&cost=10&__cf_chl_tk=gFNTKHMGO7AW4bwZ3WN.ioiepI5sjz7pfEtxT6GySgA-1744272415-1.0.1.1-lw6FtnweA2u1c4RtL5WyadKedanXJbTP8o1j3s0eQY8'
    }


async def __get_coin_info(address: str) -> CoinInfo:
    name = ''.join(random.choices(string.ascii_lowercase, k=5))
    return CoinInfo(address, name.upper(), name.title(), '')


async def get_coins_info(addresses: list[str], chain: str) -> list[CoinInfo]:
    data = {
        'chain': chain,  # sol
        'addresses': addresses,  # EQ8XnCvwZvhdJZZZeJeRv5bYyNTz5vQ4TL9VFxwCPcZc
    }
    async with ClientSession(settings.GMGN_API_URL) as session:
        async with session.post(
            'mutil_window_token_info',
            headers=get_headers(),
            cookies={'cf_clearance': settings.GMGN_COOKIE},
            json=data,
        ) as rsp:
            data = await rsp.json()
            # logger.info(json.dumps(data, indent=4))
            return [
                CoinInfo(i['address'], i['symbol'], i['logo'], i['name'])
                for i in data['data']
            ]


async def get_coin_info(address: str, chain: str) -> CoinInfo:
    return (await get_coins_info([address], chain))[0]


async def get_wallet_activity(
    address: str, chain: str
) -> list[WalletActivity]:
    params = {
        'wallet': address,  # 71CPXu3TvH3iUKaY1bNkAAow24k6tjH473SsKprQBABC
    }
    async with ClientSession(settings.GMGN_API_URL) as session:
        async with session.get(
            f'wallet_activity/{chain}',
            headers=get_headers(),
            params=params,
        ) as rsp:
            data = await rsp.json()
            # logger.info(json.dumps(data, indent=4))
            return [
                WalletActivity(
                    i['cost_usd'],
                    i['price_usd'],
                    BaseCoinInfo(**i['token']),
                    i['token_amount'],
                    i['timestamp'],
                )
                for i in data['data']['activities']
            ]
