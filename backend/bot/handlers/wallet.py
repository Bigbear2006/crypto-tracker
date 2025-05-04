from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from django.db import IntegrityError

from bot.exceptions import WalletNotFound
from bot.keyboards.inline import (
    cancel_kb,
    get_wallets_list_keyboard,
    wallet_kb,
)
from bot.keyboards.utils import one_button_keyboard
from bot.states import WalletState
from core.models import ClientWallet, Wallet

router = Router()


@router.message(Command('add_wallet'))
async def add_wallet(msg: Message, state: FSMContext):
    await state.set_state(WalletState.address)
    await msg.answer('Введите адрес кошелька', reply_markup=cancel_kb)


@router.message(F.text, StateFilter(WalletState.address))
async def add_or_update_wallet(msg: Message, state: FSMContext):
    address = msg.text
    chain = 'solana-mainnet'

    try:
        if wallet_id := await state.get_value('wallet_id'):
            wallet, _ = await Wallet.objects.aget_or_create(
                address=address,
                chain=chain,
            )
            await ClientWallet.objects.filter(
                wallet_id=wallet_id,
                client_id=msg.chat.id,
            ).aupdate(
                wallet=wallet,
            )
        else:
            wallet = await Wallet.objects.add_to_client(
                address,
                chain,
                msg.chat.id,
            )
    except IntegrityError:
        text = 'Такой кошелёк уже добавлен'
    except WalletNotFound:
        text = 'Такого кошелька не существует'
    else:
        text = f'Кошелёк {wallet.address} добавлен'

    await state.clear()
    await msg.answer(
        text,
        reply_markup=one_button_keyboard(
            text='К списку кошельков',
            callback_data='wallets_list',
        ),
    )


@router.message(Command('edit_wallet'))
@router.callback_query(F.data == 'wallets_list')
async def wallets_list(msg: Message | CallbackQuery, state: FSMContext):
    client_id = (
        msg.chat.id if isinstance(msg, Message) else msg.message.chat.id
    )
    answer_func = (
        msg.answer if isinstance(msg, Message) else msg.message.edit_text
    )
    await state.update_data(wallet_id=None)
    await answer_func(
        text='Кошельки, которые вы отслеживаете',
        reply_markup=await get_wallets_list_keyboard(client_id),
    )


@router.callback_query(F.data.in_(('wallets_previous', 'wallets_next')))
async def change_wallet_page(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    page = data.get('page', 1)

    if query.data == 'wallets_previous':
        page -= 1
    else:
        page += 1

    await state.update_data(page=page)
    await query.message.edit_text(
        'Кошельки, которые вы отслеживаете',
        reply_markup=await get_wallets_list_keyboard(
            query.message.chat.id,
            page=page,
        ),
    )


@router.callback_query(F.data.startswith('wallet'))
async def wallet_detail(query: CallbackQuery, state: FSMContext):
    wallet = await Wallet.objects.aget(pk=query.data.split('_')[-1])
    await state.update_data(wallet_id=wallet.pk)
    await query.message.edit_text(
        f'Кошелёк {wallet.address}',
        reply_markup=wallet_kb,
    )


@router.callback_query(F.data == 'edit_wallet')
async def edit_wallet(query: CallbackQuery, state: FSMContext):
    await state.set_state(WalletState.address)
    await query.message.edit_text(
        'Введите адрес кошелька',
        reply_markup=cancel_kb,
    )


@router.callback_query(F.data == 'delete_wallet')
async def delete_wallet(query: CallbackQuery, state: FSMContext):
    await ClientWallet.objects.filter(
        wallet_id=await state.get_value('wallet_id'),
        client_id=query.message.chat.id,
    ).adelete()

    await state.update_data(wallet_id=None)
    await query.message.edit_text(
        'Кошельки, которые вы отслеживаете',
        reply_markup=await get_wallets_list_keyboard(query.message.chat.id),
    )
