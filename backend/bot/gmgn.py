import json

from aiohttp import ClientSession

from bot.settings import settings


def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/134.0.0.0 Safari/537.36',
        'Cookie': '',
    }


async def coin():
    data = {
        'chain': 'sol',
        'addresses': ['7tJCkYgtmq73WvvCYx8BfZAbCCzv25gFvRZr2TQdpNbF'],
    }

    async with ClientSession(settings.GMGN_API_URL) as session:
        async with session.post(
            'mutil_window_token_info',
            headers=get_headers(),
            json=data,
        ) as rsp:
            data = await rsp.json()
            print(json.dumps(data, indent=4))
            return data


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
            print(json.dumps(data, indent=4))
            return data
