from dataclasses import asdict

from bot.api.birdeye import BirdEyeAPI
from bot.schemas import TokenInfo, TokenListParams
from bot.services.coin import bulk_get_or_create_coins
from core.models import ClientFilters


def filter_results(
    f: ClientFilters,
    *,
    results: list[dict] | list[TokenInfo] | None = None,
    return_str: bool = True,
) -> list[TokenInfo] | list[str]:
    if not results:
        results = f.results

    if not results:
        return []

    if isinstance(results[0], TokenInfo):
        results = [asdict(i) for i in results]

    return [
        TokenInfo(**i).message_text if return_str else TokenInfo(**i)
        for i in results
        if (
            (f.min_price is None or i['price'] >= f.min_price)
            and (f.max_price is None or i['price'] <= f.max_price)
            and (f.min_age == 0 or i.get('age', 0) >= f.min_age)
            and (f.max_age is None or i.get('age', 0) <= f.max_age)
            and i['market_cap'] >= f.min_market_cap
        )
    ]


async def add_date_to_coins(results: list[dict]) -> list[dict]:
    coins = await bulk_get_or_create_coins(
        'solana',
        [i['address'] for i in results],
    )
    results = [
        {**i, 'age': coins[i['address']].age}
        for i in results
        if i['address'] in coins
    ]
    return results


async def get_and_filter_results(
    api: BirdEyeAPI,
    f: ClientFilters,
    params: TokenListParams,
):
    return filter_results(
        f,
        results=await add_date_to_coins(
            [asdict(i) for i in await api.get_token_list(params)],
        ),
        return_str=False,
    )
