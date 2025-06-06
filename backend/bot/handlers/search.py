from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.api.birdeye import BirdEyeAPI
from bot.keyboards.inline import cancel_kb, search_kb, to_search_kb
from bot.parse import parse_message
from bot.schemas import TokenListParams
from bot.services.client_filters import (
    add_date_to_coins,
    filter_results,
    get_and_filter_results,
)
from bot.states import SearchState
from bot.text_utils import parse_age
from core.models import ClientFilters

router = Router()


async def set_search_filter(
    msg: Message,
    state: FSMContext,
    *,
    field: str,
    parse_func: Callable[[str], Any],
    error_text: str,
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

    extra_data = {}
    data = await state.get_data()
    f = await ClientFilters.objects.get_by_id(msg.chat.id)

    if field == 'min_liquidity':
        async with BirdEyeAPI() as api:
            results = await get_and_filter_results(
                api,
                f,
                TokenListParams(min_liquidity=value),
            )
            extra_data = {'results': [asdict(i) for i in results]}

    if field in ('min_age', 'max_age') and not data.get('ages_is_set', False):
        results = await add_date_to_coins(f.results)
        await state.update_data(ages_is_set=True)
        extra_data = {'results': results}

    await ClientFilters.objects.update_by_id(
        msg.chat.id,
        **{field: value},
        **extra_data,
    )

    await msg.answer(**await get_search_menu_data(msg.chat.id))
    await state.set_state()


async def get_search_menu_data(client_id: int | str):
    filters = await ClientFilters.objects.get_by_id(client_id)
    results = filter_results(filters)
    return {
        'text': (
            f'Найдено {len(results)} монет.\n'
            f'Фильтры:\n{filters.message_text}\n'
            f'Вы можете установить дополнительные фильтры ниже'
        ),
        'reply_markup': search_kb,
    }


@router.message(Command('search'))
async def search(msg: Message, state: FSMContext):
    if await ClientFilters.objects.get_by_id(msg.chat.id):
        await msg.answer(**await get_search_menu_data(msg.chat.id))
        return

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

    await ClientFilters.objects.acreate(
        client_id=msg.chat.id,
        min_liquidity=min_liquidity,
        results=[asdict(i) for i in results],
    )
    await msg.answer(**await get_search_menu_data(msg.chat.id))
    await state.set_state()


@router.callback_query(F.data == 'to_search')
async def to_search(query: CallbackQuery, state: FSMContext):
    await state.set_state()
    await query.message.edit_text(
        **await get_search_menu_data(query.message.chat.id),
    )


@router.callback_query(F.data.startswith('search_filter'))
async def set_search_filter_handler(query: CallbackQuery, state: FSMContext):
    texts = {
        'min_liquidity': 'Введите минимальную ликвидность',
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
    )


@router.callback_query(F.data == 'show_search_results')
async def show_search_results(query: CallbackQuery):
    filters = await ClientFilters.objects.get_by_id(query.message.chat.id)
    results = '\n'.join(filter_results(filters))

    await query.message.edit_text(
        f'Результаты поиска:\n{results[:4000]}',
        reply_markup=to_search_kb,
    )

    if len(results) > 4000:
        await query.message.answer(
            results[4000:8000],
            reply_markup=to_search_kb,
        )
