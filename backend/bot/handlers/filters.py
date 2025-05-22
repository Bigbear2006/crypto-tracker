from collections.abc import Callable
from typing import Any

from aiogram import F, Router, flags
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import filters_kb, to_filters_kb
from bot.states import FiltersState
from bot.text_utils import age_to_str, parse_age, price_to_str
from core.models import Client

router = Router()


@router.message(Command('filters'))
@router.callback_query(F.data == 'to_filters')
@flags.with_client
async def set_filters_handler(
    msg: Message | CallbackQuery,
    state: FSMContext,
    client: Client,
):
    answer_func = (
        msg.answer if isinstance(msg, Message) else msg.message.edit_text
    )
    await state.clear()
    await answer_func(
        'Ваши фильтры:\n'
        f'Максимальная цена монеты: '
        f'{price_to_str(client.max_coin_price)}\n'
        f'Минимальная капитализация монеты: '
        f'{price_to_str(client.min_coin_market_cap)}\n'
        f'Минимальный возраст монеты: {age_to_str(client.min_coin_age)}\n'
        f'Максимальный возраст монеты: {age_to_str(client.max_coin_age)}\n',
        reply_markup=filters_kb,
    )


@router.callback_query(F.data.startswith('filter'))
async def set_filters_handler_2(query: CallbackQuery, state: FSMContext):
    texts = {
        'max_coin_price': 'Введите максимальную цену монеты. Пример: 4.5',
        'min_coin_market_cap': (
            'Введите минимальную рыночную капитализацию монеты. Пример: 1000'
        ),
        'min_coin_age': (
            'Введите минимальный возраст монеты. '
            'Примеры: 15 минут, 2 часа, 1 день.'
        ),
        'max_coin_age': (
            'Введите максимальный возраст монеты. '
            'Примеры: 15 минут, 2 часа, 1 день.'
        ),
    }

    coin_filter = query.data.split(':')[-1]
    await state.set_state(getattr(FiltersState, coin_filter))
    await query.message.edit_text(
        texts[coin_filter],
        reply_markup=to_filters_kb,
    )


async def parse_message(
    msg: Message,
    *,
    parse_func: Callable[[str], Any],
    exceptions=(ValueError,),
) -> Any:
    try:
        value = parse_func(msg.text)
        return value
    except exceptions:
        return


async def set_filter(
    msg: Message,
    state: FSMContext,
    *,
    field: str,
    parse_func: Callable[[str], Any],
    error_text: str,
    success_text: Callable[[Any], str],
    exceptions=(ValueError,),
):
    value = await parse_message(
        msg,
        parse_func=parse_func,
        exceptions=exceptions,
    )

    if not value:
        await msg.answer(error_text, reply_markup=to_filters_kb)
        return

    await Client.objects.filter(pk=msg.chat.id).aupdate(
        **{field: value},
    )

    await state.clear()
    await msg.answer(
        success_text(value),
        reply_markup=to_filters_kb,
    )


@router.message(F.text, StateFilter(FiltersState.max_coin_price))
async def set_max_coin_price(msg: Message, state: FSMContext):
    await set_filter(
        msg,
        state,
        field='max_coin_price',
        parse_func=float,
        error_text='Вы ввели некорректное число. Попробуйте еще раз',
        success_text=lambda x: f'Теперь максимальная цена монеты равна {x}',
    )


@router.message(F.text, StateFilter(FiltersState.min_coin_market_cap))
async def set_min_coin_market_cap(msg: Message, state: FSMContext):
    await set_filter(
        msg,
        state,
        field='min_coin_market_cap',
        parse_func=float,
        error_text='Вы ввели некорректное число. Попробуйте еще раз',
        success_text=lambda x: (
            f'Теперь минимальная капитализация монеты равна {x}'
        ),
    )


@router.message(F.text, StateFilter(FiltersState.min_coin_age))
async def set_min_coin_age(msg: Message, state: FSMContext):
    await set_filter(
        msg,
        state,
        field='min_coin_age',
        parse_func=parse_age,
        error_text='Вы ввели некорректное число. Попробуйте еще раз',
        success_text=lambda x: (
            f'Теперь минимальный возраст монеты равен {age_to_str(x)}'
        ),
    )


@router.message(F.text, StateFilter(FiltersState.max_coin_age))
async def set_max_coin_age(msg: Message, state: FSMContext):
    await set_filter(
        msg,
        state,
        field='max_coin_age',
        parse_func=parse_age,
        error_text='Вы ввели некорректное число. Попробуйте еще раз',
        success_text=lambda x: (
            f'Теперь максимальный возраст монеты равен {age_to_str(x)}'
        ),
    )
