from aiogram import F, Router, flags
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from django.db import IntegrityError

from bot.keyboards.inline import (
    coin_kb,
    get_coin_tracking_params_kb,
    get_coins_list_keyboard,
)
from bot.loader import logger
from bot.states import CoinState
from core.models import Client, ClientCoin, Coin, CoinTrackingParams

router = Router()


@router.message(Command('add_coin'))
@flags.with_client
async def add_coin(
    msg: Message,
    state: FSMContext,
    command: CommandObject,
    client: Client,
):
    if not command.args:
        await state.set_state(CoinState.address)
        await msg.answer('Введите адрес монеты')
        return

    try:
        coin = await Coin.objects.add_to_client(command.args, client.pk)
    except IntegrityError:
        await msg.answer('Такая монета уже добавлена')
        return

    await msg.answer(f'Монета {coin.name} добавлена')


@router.message(F.text, StateFilter(CoinState.address))
async def add_or_update_coin(msg: Message, state: FSMContext):
    if coin_id := await state.get_value('coin_id'):
        logger.info('1')
        coin, _ = await Coin.objects.aget_or_create(address=msg.text)
        try:
            await ClientCoin.objects.filter(
                coin_id=coin_id,
                client_id=msg.chat.id,
            ).aupdate(
                coin=coin,
            )
            logger.info('2')
        except IntegrityError:
            await msg.answer('Такая монета уже добавлена')
            return
    else:
        logger.info('3')
        try:
            coin = await Coin.objects.add_to_client(msg.text, msg.chat.id)
        except IntegrityError:
            await msg.answer('Такая монета уже добавлена')
            return

    await state.clear()
    await msg.answer(f'Монета {coin.name} добавлена')


@router.message(Command('track_coin'))
async def track_coin(msg: Message):
    pass


@router.message(Command('edit_coin'))
async def coins_list(msg: Message, state: FSMContext):
    await state.update_data(coin_id=None)
    await msg.answer(
        'Монеты, которые вы отслеживаете',
        reply_markup=await get_coins_list_keyboard(msg.chat.id),
    )


@router.callback_query(F.data == 'coins_list')
async def to_coins_list(query: CallbackQuery, state: FSMContext):
    await state.update_data(coin_id=None)
    await query.message.edit_text(
        'Монеты, которые вы отслеживаете',
        reply_markup=await get_coins_list_keyboard(query.message.chat.id),
    )


@router.callback_query(F.data.startswith('coin'))
async def coin_detail(query: CallbackQuery, state: FSMContext):
    coin = await Coin.objects.aget(pk=query.data.split('_')[-1])
    await state.update_data(coin_id=coin.pk)
    await query.message.edit_text(
        f'Монета {coin.symbol} ({coin.name})\nАдрес: {coin.address}',
        reply_markup=coin_kb,
    )


@router.callback_query(F.data == 'edit_coin')
async def edit_coin(query: CallbackQuery, state: FSMContext):
    await state.set_state(CoinState.address)
    await query.message.answer('Введите адрес монеты')


@router.callback_query(F.data == 'delete_coin')
async def delete_coin(query: CallbackQuery, state: FSMContext):
    await ClientCoin.objects.filter(
        coin_id=await state.get_value('coin_id'),
        client_id=query.message.chat.id,
    ).adelete()

    await state.update_data(coin_id=None)
    await query.message.edit_text(
        'Монеты, которые вы отслеживаете',
        reply_markup=await get_coins_list_keyboard(query.message.chat.id),
    )


@router.callback_query(F.data == 'set_coin_tracking_params')
async def set_coin_tracking_params(query: CallbackQuery, state: FSMContext):
    client_coin = await ClientCoin.objects.aget(
        coin_id=await state.get_value('coin_id'),
        client_id=query.message.chat.id,
    )

    if client_coin.tracking_param:
        tracking_param = CoinTrackingParams(client_coin.tracking_param).label
    else:
        tracking_param = 'Нет'

    try:
        await query.message.answer(
            f'Параметр отслеживания: {tracking_param}',
            reply_markup=await get_coin_tracking_params_kb(),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.in_(CoinTrackingParams.values))
async def toggle_tracking_params(
    query: CallbackQuery,
    state: FSMContext,
):
    await ClientCoin.objects.filter(
        coin_id=await state.get_value('coin_id'),
        client_id=query.message.chat.id,
    ).aupdate()

    tracking_param = CoinTrackingParams(query.data).label
    try:
        await query.message.edit_text(
            f'Параметр отслеживания: {tracking_param}',
            reply_markup=await get_coin_tracking_params_kb(),
        )
    except TelegramBadRequest:
        pass
