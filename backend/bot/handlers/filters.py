from datetime import UTC, datetime

from aiogram import F, Router, flags
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import filters_kb, to_filters_kb
from bot.settings import settings
from bot.states import FiltersState
from core.models import Client

router = Router()


@router.message(Command('filters'))
@router.callback_query(F.data == 'to_filters')
@flags.with_client
async def set_filters(
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
        f'{client.max_coin_price or "Нет"}\n'
        f'Минимальная капитализация монеты: '
        f'{client.min_coin_market_cap or "Нет"}\n'
        f'Максимальная дата создания монеты: '
        f'{client.max_coin_creation_date.strftime(settings.DATE_FMT) if client.max_coin_creation_date else "Нет"}\n',
        reply_markup=filters_kb,
    )


@router.callback_query(F.data.startswith('filter'))
async def set_filters_2(query: CallbackQuery, state: FSMContext):
    texts = {
        'max_coin_price': 'Введите максимальную цену монеты. Пример: 4.5',
        'min_coin_market_cap': (
            'Введите минимальную рыночную капитализацию монеты. Пример: 1000'
        ),
        'max_coin_creation_date': (
            'Введите максимальную дату создания монеты в формате ДД.ММ.ГГГГ.\n'
        ),
    }

    coin_filter = query.data.split(':')[-1]
    await state.set_state(getattr(FiltersState, coin_filter))
    await query.message.edit_text(
        texts[coin_filter],
        reply_markup=to_filters_kb,
    )


@router.message(F.text, StateFilter(FiltersState.max_coin_price))
async def set_max_coin_price(msg: Message):
    try:
        max_coin_price = float(msg.text)
    except ValueError:
        await msg.answer('Вы ввели некорректное число. Попробуйте еще раз')
        return

    await Client.objects.filter(pk=msg.chat.id).aupdate(
        max_coin_price=max_coin_price,
    )
    await msg.answer(
        f'Теперь максимальная цена монеты равна {max_coin_price}',
        reply_markup=to_filters_kb,
    )


@router.message(F.text, StateFilter(FiltersState.min_coin_market_cap))
async def set_min_coin_market_cap(msg: Message):
    try:
        min_coin_market_cap = float(msg.text)
    except ValueError:
        await msg.answer('Вы ввели некорректное число. Попробуйте еще раз')
        return

    await Client.objects.filter(pk=msg.chat.id).aupdate(
        min_coin_market_cap=min_coin_market_cap,
    )
    await msg.answer(
        f'Теперь минимальная капитализация монеты равна {min_coin_market_cap}',
        reply_markup=to_filters_kb,
    )


@router.message(F.text, StateFilter(FiltersState.max_coin_creation_date))
async def set_max_coin_creation_date(msg: Message):
    try:
        max_coin_creation_date = datetime.strptime(
            msg.text,
            settings.DATE_FMT,
        ).replace(tzinfo=UTC)
    except ValueError:
        await msg.answer('Вы ввели некорректную дату. Попробуйте еще раз')
        return

    await Client.objects.filter(pk=msg.chat.id).aupdate(
        max_coin_creation_date=max_coin_creation_date,
    )
    await msg.answer(
        f'Теперь максимальная дата создания монеты равна '
        f'{max_coin_creation_date.strftime(settings.DATE_FMT)}',
        reply_markup=to_filters_kb,
    )
