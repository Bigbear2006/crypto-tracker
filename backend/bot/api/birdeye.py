from dataclasses import asdict

from bot.api.base import APIClient
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

    async def get_token_list(self, params: TokenListParams) -> list[TokenInfo]:
        async with self.session.get(
            'defi/tokenlist',
            params=asdict(params, dict_factory=exclude_none_dict_factory),
        ) as rsp:
            data = await rsp.json()
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
