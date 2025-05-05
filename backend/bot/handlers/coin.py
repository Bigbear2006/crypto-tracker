from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from django.db import IntegrityError

from bot.api.alchemy import AlchemyAPI
from bot.exceptions import CoinNotFound
from bot.keyboards.inline import (
    cancel_kb,
    coin_kb,
    get_coin_tracking_params_kb,
    get_coins_list_keyboard,
)
from bot.keyboards.utils import one_button_keyboard
from bot.states import CoinState
from core.models import ClientCoin, Coin, CoinTrackingParams

router = Router()


@router.message(Command('add_coin'))
async def add_coin(msg: Message, state: FSMContext):
    await state.set_state(CoinState.address)
    await msg.answer('Введите адрес монеты', reply_markup=cancel_kb)


@router.message(F.text, StateFilter(CoinState.address))
async def add_or_update_coin(msg: Message, state: FSMContext):
    address = msg.text
    chain = 'solana'

    try:
        if coin_id := await state.get_value('coin_id'):
            coin = await Coin.objects.update_client_coin(
                address,
                chain,
                client_id=msg.chat.id,
                coin_id=coin_id,
            )
        else:
            coin = await Coin.objects.add_to_client(
                address,
                chain,
                msg.chat.id,
            )
    except IntegrityError:
        text = 'Такая монета уже добавлена'
    except CoinNotFound:
        text = 'Такой монеты не существует'
    else:
        text = f'Монета {coin.symbol} ({coin.name}) добавлена'

    await state.clear()
    await msg.answer(
        text,
        reply_markup=one_button_keyboard(
            text='К списку монет',
            callback_data='coins_list',
        ),
    )


@router.message(Command('edit_coin'))
@router.callback_query(F.data == 'coins_list')
async def coins_list(msg: Message | CallbackQuery, state: FSMContext):
    client_id = (
        msg.chat.id if isinstance(msg, Message) else msg.message.chat.id
    )
    answer_func = (
        msg.answer if isinstance(msg, Message) else msg.message.edit_text
    )
    await state.update_data(coin_id=None, coin_address=None)
    await answer_func(
        text='Монеты, которые вы отслеживаете',
        reply_markup=await get_coins_list_keyboard(client_id),
    )


@router.callback_query(F.data.in_(('coins_previous', 'coins_next')))
async def change_coin_page(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    page = data.get('page', 1)

    if query.data == 'coins_previous':
        page -= 1
    else:
        page += 1

    await state.update_data(page=page)
    await query.message.edit_text(
        'Монеты, которые вы отслеживаете',
        reply_markup=await get_coins_list_keyboard(
            query.message.chat.id,
            page=page,
        ),
    )


@router.callback_query(F.data.startswith('coin'))
async def coin_detail(query: CallbackQuery, state: FSMContext):
    coin = await Coin.objects.aget(pk=query.data.split('_')[-1])
    client_coin = await ClientCoin.objects.aget(
        coin=coin,
        client_id=query.message.chat.id,
    )

    if client_coin.tracking_param:
        tracking_param = CoinTrackingParams(client_coin.tracking_param).label
    else:
        tracking_param = 'Нет'

    await state.update_data(coin_id=coin.pk, coin_address=coin.address)
    await query.message.edit_text(
        f'Монета {coin.symbol} ({coin.name})\n'
        f'Адрес: {coin.address}\n\n'
        f'Параметр отслеживания: {tracking_param}\n'
        f'Отслеживаемая цена: {client_coin.tracking_price or "Нет"}',
        reply_markup=coin_kb,
    )


@router.callback_query(F.data == 'edit_coin')
async def edit_coin(query: CallbackQuery, state: FSMContext):
    await state.set_state(CoinState.address)
    await query.message.answer(
        'Введите адрес монеты',
        reply_markup=cancel_kb,
    )


@router.callback_query(F.data == 'delete_coin')
async def delete_coin(query: CallbackQuery, state: FSMContext):
    await ClientCoin.objects.filter(
        coin_id=await state.get_value('coin_id'),
        client_id=query.message.chat.id,
    ).adelete()

    await state.update_data(coin_id=None, coin_address=None)
    await query.message.edit_text(
        'Монеты, которые вы отслеживаете',
        reply_markup=await get_coins_list_keyboard(query.message.chat.id),
    )


@router.callback_query(F.data == 'set_coin_tracking_params')
async def set_coin_tracking_params(query: CallbackQuery, state: FSMContext):
    coin_id = await state.get_value('coin_id')
    client_coin = await ClientCoin.objects.aget(
        coin_id=coin_id,
        client_id=query.message.chat.id,
    )

    if client_coin.tracking_param:
        tracking_param = CoinTrackingParams(client_coin.tracking_param).label
    else:
        tracking_param = 'Нет'

    try:
        await query.message.edit_text(
            f'Параметр отслеживания: {tracking_param}',
            reply_markup=await get_coin_tracking_params_kb(
                back_button_data=f'coin_{coin_id}',
            ),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == 'set_coin_tracking_price')
async def set_coin_tracking_price(query: CallbackQuery, state: FSMContext):
    await state.set_state(CoinState.tracking_price)
    await query.message.answer(
        'Введите цену для уведомления. Пример: 1.02',
        reply_markup=cancel_kb,
    )


@router.message(F.text, StateFilter(CoinState.tracking_price))
async def set_coin_tracking_price_2(msg: Message, state: FSMContext):
    try:
        tracking_price = float(msg.text)
    except ValueError:
        await msg.answer(
            'Вы ввели некорректную цену, попробуйте еще раз',
            reply_markup=cancel_kb,
        )
        return

    tracking_param = ''
    text = f'Теперь отслеживаемая цена этой монеты: {tracking_price}\n'
    coin = await Coin.objects.aget(pk=await state.get_value('coin_id'))
    client_coin = await ClientCoin.objects.aget(
        coin=coin,
        client_id=msg.chat.id,
    )
    async with AlchemyAPI() as api:
        coin_price = await api.get_coin_price(coin.chain, coin.address)

    if client_coin.tracking_param:
        if (
            client_coin.tracking_param == CoinTrackingParams.PRICE_UP
            and tracking_price <= coin_price.price
        ):
            param_str = 'больше'
        elif (
            client_coin.tracking_param == CoinTrackingParams.PRICE_DOWN
            and tracking_price >= coin_price.price
        ):
            param_str = 'меньше'
        else:
            param_str = None

        if param_str:
            await msg.answer(
                f'Текущая цена монеты (${coin_price.price}) '
                f'уже {param_str} или равна указанному значению'
                f' (${tracking_price})\n'
                f'Укажите другую цену или измените '
                f'параметр отслеживания в настройках',
                reply_markup=cancel_kb,
            )
            return
    else:
        tracking_param = (
            CoinTrackingParams.PRICE_UP
            if tracking_price > coin_price.price
            else CoinTrackingParams.PRICE_DOWN
        )
        text += (
            f'Автоматически установлен параметр отслеживания: '
            f'{tracking_param.label}'
        )

    await ClientCoin.objects.filter(
        coin=coin,
        client_id=msg.chat.id,
    ).aupdate(
        tracking_price=tracking_price,
        notification_sent=False,
        **{'tracking_param': tracking_param} if tracking_param else {},
    )

    await msg.answer(
        text,
        reply_markup=one_button_keyboard(
            text='Назад',
            callback_data=f'coin_{coin.pk}',
        ),
    )
    await state.set_state(None)


@router.callback_query(F.data.in_(CoinTrackingParams.values))
async def toggle_tracking_params(
    query: CallbackQuery,
    state: FSMContext,
):
    coin_id = await state.get_value('coin_id')
    await ClientCoin.objects.filter(
        coin_id=coin_id,
        client_id=query.message.chat.id,
    ).aupdate(tracking_param=query.data, notification_sent=False)
    tracking_param = CoinTrackingParams(query.data).label

    try:
        await query.message.edit_text(
            f'Параметр отслеживания: {tracking_param}',
            reply_markup=await get_coin_tracking_params_kb(
                back_button_data=f'coin_{coin_id}',
            ),
        )
    except TelegramBadRequest:
        pass
