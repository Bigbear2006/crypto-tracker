from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from django.db import IntegrityError

from bot.exceptions import WalletNotFound
from bot.keyboards.inline import (
    chains_kb,
    get_wallets_list_keyboard,
    wallet_kb,
)
from bot.states import WalletState
from core.models import ClientWallet, Wallet

router = Router()


@router.message(Command('add_wallet'))
async def add_wallet(
    msg: Message,
    state: FSMContext,
    command: CommandObject,
):
    if not command.args:
        await state.set_state(WalletState.address)
        await msg.answer('Введите адрес кошелька')
        return

    await state.update_data(wallet_address=command.args)
    await state.set_state(WalletState.chain)
    await msg.answer('Выберите блокчейн кошелька', reply_markup=chains_kb)


@router.message(F.text, StateFilter(WalletState.address))
async def set_wallet_address(msg: Message, state: FSMContext):
    await state.update_data(wallet_address=msg.text)
    await state.set_state(WalletState.chain)
    await msg.answer('Выберите блокчейн кошелька', reply_markup=chains_kb)


@router.callback_query(
    F.data.startswith('chain'),
    StateFilter(WalletState.chain),
)
async def add_or_update_wallet(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    address = data['wallet_address']
    chain = query.data.split('_')[1]

    try:
        if wallet_id := data.get('wallet_id'):
            wallet, _ = await Wallet.objects.aget_or_create(
                address=address,
                chain=chain,
            )
            await ClientWallet.objects.filter(
                wallet_id=wallet_id,
                client_id=query.message.chat.id,
            ).aupdate(
                wallet=wallet,
            )
        else:
            wallet = await Wallet.objects.add_to_client(
                address,
                chain,
                query.message.chat.id,
            )
    except IntegrityError:
        text = 'Такой кошелёк уже добавлен'
    except WalletNotFound:
        text = 'Такого кошелька не существует'
    else:
        text = f'Кошелёк {wallet.address} ({wallet.chain}) добавлен'

    await state.clear()
    await query.message.edit_text(text, reply_markup=None)


@router.message(Command('edit_wallet'))
async def wallets_list(msg: Message, state: FSMContext):
    await state.update_data(wallet_id=None)
    await msg.answer(
        'Кошельки, которые вы отслеживаете',
        reply_markup=await get_wallets_list_keyboard(msg.chat.id),
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


@router.callback_query(F.data == 'wallets_list')
async def to_wallets_list(query: CallbackQuery, state: FSMContext):
    await state.update_data(wallet_id=None, wallet_address=None)
    await query.message.edit_text(
        'Кошельки, которые вы отслеживаете',
        reply_markup=await get_wallets_list_keyboard(query.message.chat.id),
    )


@router.callback_query(F.data.startswith('wallet'))
async def wallet_detail(query: CallbackQuery, state: FSMContext):
    wallet = await Wallet.objects.aget(pk=query.data.split('_')[-1])
    await state.update_data(wallet_id=wallet.pk, wallet_address=wallet.address)
    await query.message.edit_text(
        f'Кошелёк {wallet.address} ({wallet.chain})',
        reply_markup=wallet_kb,
    )


@router.callback_query(F.data == 'edit_wallet')
async def edit_wallet(query: CallbackQuery, state: FSMContext):
    await state.set_state(WalletState.chain)
    await query.message.edit_text(
        'Выберите блокчейн кошелька',
        reply_markup=chains_kb,
    )


@router.callback_query(F.data == 'delete_wallet')
async def delete_wallet(query: CallbackQuery, state: FSMContext):
    await ClientWallet.objects.filter(
        wallet_id=await state.get_value('wallet_id'),
        client_id=query.message.chat.id,
    ).adelete()

    await state.update_data(wallet_id=None, wallet_address=None)
    await query.message.edit_text(
        'Кошельки, которые вы отслеживаете',
        reply_markup=await get_wallets_list_keyboard(query.message.chat.id),
    )
