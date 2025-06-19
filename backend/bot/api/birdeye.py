import asyncio
import random
from dataclasses import asdict

from bot.api.base import APIClient
from bot.exceptions import BirdEyeBadRequest
from bot.loader import logger
from bot.schemas import TokenInfo, TokenListParams, exclude_none_dict_factory
from bot.settings import settings


class BirdEyeAPI(APIClient):
    def __init__(self, **sessions_kwargs):
        headers = sessions_kwargs.get('headers', {})
        sessions_kwargs['headers'] = {**headers, **self.headers}
        super().__init__('https://public-api.birdeye.so/', **sessions_kwargs)

    @property
    def headers(self):
        return {
            'x-chain': 'solana',
            'x-api-key': settings.BIRDEYE_API_KEY,
        }

    async def get_token_list(
        self,
        params: TokenListParams,
        *,
        retries: int = 2,
        raise_if_empty: bool = False,
    ) -> list[TokenInfo]:
        async with self.session.get(
            'defi/tokenlist',
            params=asdict(params, dict_factory=exclude_none_dict_factory),
        ) as rsp:
            data = await rsp.json()
            logger.info(params)

        msg = data.get('message', '')
        if msg == 'Bad request':
            raise BirdEyeBadRequest(msg)

        if not data.get('data') and retries > 0:
            logger.info(data)
            await asyncio.sleep(random.randint(3, 15))
            return await self.get_token_list(params, retries=retries - 1)

        if raise_if_empty and not data['data']['tokens']:
            raise BirdEyeBadRequest('Got 0 results')

        return [
            TokenInfo(
                address=i['address'],
                symbol=i['symbol'],
                logo=i['logoURI'],
                name=i['name'],
                market_cap=i['mc'],
                price=i['price'],
                liquidity=i['liquidity'],
            )
            for i in data['data']['tokens']
        ]
