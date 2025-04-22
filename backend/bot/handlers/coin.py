from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from django.db import IntegrityError

from bot.exceptions import CoinNotFound
from bot.keyboards.inline import (
    chains_kb,
    coin_kb,
    get_coin_tracking_params_kb,
    get_coins_list_keyboard,
)
from bot.keyboards.utils import one_button_keyboard
from bot.states import CoinState
from core.models import ClientCoin, Coin, CoinTrackingParams

router = Router()


@router.message(Command('add_coin'))
async def add_coin(
    msg: Message,
    state: FSMContext,
    command: CommandObject,
):
    if not command.args:
        await state.set_state(CoinState.address)
        await msg.answer('Введите адрес монеты')
        return

    await state.update_data(coin_address=command.args)
    await state.set_state(CoinState.chain)
    await msg.answer('Выберите блокчейн кошелька', reply_markup=chains_kb)


@router.message(F.text, StateFilter(CoinState.address))
async def set_coin_address(msg: Message, state: FSMContext):
    await state.update_data(coin_address=msg.text)
    await state.set_state(CoinState.chain)
    await msg.answer('Выберите блокчейн монеты', reply_markup=chains_kb)


@router.callback_query(
    F.data.startswith('chain'),
    StateFilter(CoinState.chain),
)
async def add_or_update_coin(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    address = data['coin_address']
    chain = query.data.split('_')[1]

    try:
        if coin_id := data.get('coin_id'):
            coin = await Coin.objects.update_client_coin(
                address,
                chain,
                client_id=query.message.chat.id,
                coin_id=coin_id,
            )
        else:
            coin = await Coin.objects.add_to_client(
                address,
                chain,
                query.message.chat.id,
            )
    except IntegrityError:
        text = 'Такая монета уже добавлена'
    except CoinNotFound:
        text = 'Такой монеты не существует'
    else:
        text = f'Монета {coin.name} добавлена'

    await state.clear()
    await query.message.edit_text(text, reply_markup=None)


@router.message(Command('edit_coin'))
async def coins_list(msg: Message, state: FSMContext):
    await state.update_data(coin_id=None)
    await msg.answer(
        'Монеты, которые вы отслеживаете',
        reply_markup=await get_coins_list_keyboard(msg.chat.id),
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


@router.callback_query(F.data == 'coins_list')
async def to_coins_list(query: CallbackQuery, state: FSMContext):
    await state.update_data(coin_id=None, coin_address=None)
    await query.message.edit_text(
        'Монеты, которые вы отслеживаете',
        reply_markup=await get_coins_list_keyboard(query.message.chat.id),
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
    await state.set_state(CoinState.chain)
    await query.message.answer(
        'Выберите блокчейн монеты',
        reply_markup=chains_kb,
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
        'Введите цену, которую вы хотите отслеживать.\nПример: 1.02',
    )


@router.message(F.text, StateFilter(CoinState.tracking_price))
async def set_coin_tracking_price_2(msg: Message, state: FSMContext):
    try:
        tracking_price = float(msg.text)
    except ValueError:
        await msg.answer('Вы ввели некорректную цену, попробуйте еще раз')
        return

    coin_id = await state.get_value('coin_id')
    await ClientCoin.objects.filter(
        coin_id=coin_id,
        client_id=msg.chat.id,
    ).aupdate(
        tracking_price=tracking_price,
    )

    await msg.answer(
        f'Теперь отслеживаемая цена этой монеты: {tracking_price}',
        reply_markup=one_button_keyboard(
            text='Назад',
            callback_data=f'coin_{coin_id}',
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
    ).aupdate(tracking_param=query.data)
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
