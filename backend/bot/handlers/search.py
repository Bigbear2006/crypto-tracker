from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.api.birdeye import BirdEyeAPI
from bot.bulk_create import bulk_get_or_create_coins
from bot.keyboards.inline import cancel_kb, search_kb, to_search_kb
from bot.parse import parse_message
from bot.schemas import SearchFilters, TokenInfo, TokenListParams
from bot.states import SearchState
from bot.text_utils import parse_age

router = Router()


def filter_results(results: list[dict], f: SearchFilters) -> list[str]:
    return [
        TokenInfo(**i).message_text
        for i in results
        if (
            (f.min_price is None or i['price'] >= f.min_price)
            and (f.max_price is None or i['price'] <= f.max_price)
            and (f.min_age == 0 or i.get('age', 0) >= f.min_age)
            and (f.max_age is None or i.get('age', 0) <= f.max_age)
            and i['market_cap'] >= f.min_market_cap
        )
    ]


async def set_search_filter(
    msg: Message,
    state: FSMContext,
    *,
    field: str,
    parse_func: Callable[[str], Any],
    error_text: str,
    success_text: Callable[[Any], str],
    exceptions=(ValueError,),
):
    value = parse_message(
        msg,
        parse_func=parse_func,
        exceptions=exceptions,
    )

    if not value:
        await msg.answer(error_text, reply_markup=to_search_kb)
        return

    data = await state.get_data()
    extra_data = {}
    if field in ('min_age', 'max_age') and not data.get('ages_is_set', False):
        coins = await bulk_get_or_create_coins(
            'solana',
            [i['address'] for i in data['results']],
        )
        results = [
            {**i, 'age': coins[i['address']].age}
            for i in data['results']
            if i['address'] in coins
        ]
        extra_data = {'results': results, 'ages_is_set': True}

    await state.update_data({field: value}, **extra_data)
    await msg.answer(success_text(value), reply_markup=to_search_kb)


@router.message(Command('search'))
async def search(msg: Message, state: FSMContext):
    await state.set_state(SearchState.min_liquidity)
    await msg.answer('Введите минимальную ликвидность', reply_markup=cancel_kb)


@router.message(F.text, StateFilter(SearchState.min_liquidity))
async def set_min_liquidity(msg: Message, state: FSMContext):
    min_liquidity = parse_message(msg, parse_func=float)
    if not min_liquidity:
        await msg.answer(
            'Вы ввели некорректное число. Попробуйте еще раз',
            reply_markup=cancel_kb,
        )
        return

    async with BirdEyeAPI() as api:
        results = await api.get_token_list(
            TokenListParams(min_liquidity=min_liquidity),
        )

    filters = SearchFilters(min_liquidity=min_liquidity)
    await state.update_data(
        results=[asdict(i) for i in results],
        **asdict(filters),
    )
    await msg.answer(
        f'Найдено {len(results)} монет.\n'
        f'Фильтры:\n{filters.message_text}\n'
        f'Вы можете установить дополнительные фильтры ниже',
        reply_markup=search_kb,
    )


@router.callback_query(F.data == 'to_search')
async def to_search(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    filters = SearchFilters.from_dict(data)
    results = filter_results(data['results'], filters)
    await state.set_state()
    await query.message.edit_text(
        f'Найдено {len(results)} монет.\n'
        f'Фильтры:\n{filters.message_text}\n'
        f'Вы можете установить дополнительные фильтры ниже',
        reply_markup=search_kb,
    )


@router.callback_query(F.data.startswith('search_filter'))
async def set_search_filter_handler(query: CallbackQuery, state: FSMContext):
    texts = {
        'min_price': 'Введите минимальную цену монеты. Пример: 4.5',
        'max_price': 'Введите максимальную цену монеты. Пример: 4.5',
        'min_age': (
            'Введите минимальный возраст монеты. '
            'Примеры: 15 минут, 2 часа, 1 день.'
        ),
        'max_age': (
            'Введите максимальный возраст монеты. '
            'Примеры: 15 минут, 2 часа, 1 день.'
        ),
        'min_market_cap': (
            'Введите минимальную рыночную капитализацию монеты. Пример: 1000'
        ),
    }

    search_filter = query.data.split(':')[-1]
    await state.update_data(field=search_filter)
    await state.set_state(SearchState.extra_filters)
    await query.message.edit_text(
        texts[search_filter],
        reply_markup=to_search_kb,
    )


@router.message(F.text, StateFilter(SearchState.extra_filters))
async def set_extra_filters(msg: Message, state: FSMContext):
    field = await state.get_value('field')
    if field in ('min_age', 'max_age'):
        parse_func = parse_age
    else:
        parse_func = float

    await set_search_filter(
        msg,
        state,
        field=field,
        parse_func=parse_func,
        error_text='Вы ввели некорректное значение. Попробуйте еще раз',
        success_text=lambda x: 'Фильтр добавлен!',
    )


@router.callback_query(F.data == 'show_search_results')
async def show_search_results(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    filters = SearchFilters.from_dict(data)
    results = '\n'.join(filter_results(data['results'], filters))

    await query.message.edit_text(f'Результаты поиска:\n{results[:4000]}')
    if len(results) > 4000:
        await query.message.answer(results[4000:8000])

    await state.clear()
