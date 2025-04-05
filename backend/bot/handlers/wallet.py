from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from django.db import IntegrityError

from bot.keyboards.inline import get_wallets_list_keyboard, wallet_kb
from bot.states import WalletState
from core.models import Client, ClientWallet, Wallet

router = Router()


@router.message(Command('add_wallet'))
async def add_wallet(msg: Message, state: FSMContext, command: CommandObject):
    if not command.args:
        await state.set_state(WalletState.address)
        await msg.answer('Введите адрес кошелька')
        return

    client, _ = await Client.objects.create_or_update_from_tg_user(
        msg.from_user,
    )

    try:
        wallet = await Wallet.objects.add_to_client(command.args, client.pk)
    except IntegrityError:
        await msg.answer('Такой кошелёк уже добавлен')
        return

    await msg.answer(f'Кошелёк {wallet.address} добавлен')


@router.message(F.text, StateFilter(WalletState.address))
async def add_or_update_wallet(msg: Message, state: FSMContext):
    client, _ = await Client.objects.create_or_update_from_tg_user(
        msg.from_user,
    )

    if wallet_id := await state.get_value('wallet_id'):
        wallet, _ = await Wallet.objects.aget_or_create(address=msg.text)
        try:
            await ClientWallet.objects.filter(
                wallet_id=wallet_id,
                client_id=client.pk,
            ).aupdate(
                wallet=wallet,
            )
        except IntegrityError:
            await msg.answer('Такой кошелёк уже добавлен')
            return
    else:
        try:
            wallet = await Wallet.objects.add_to_client(msg.text, client.pk)
        except IntegrityError:
            await msg.answer('Такой кошелёк уже добавлен')
            return

    await state.clear()
    await msg.answer(f'Кошелёк {wallet.address} добавлен')


@router.message(Command('edit_wallet'))
async def wallets_list(msg: Message):
    client, created = await Client.objects.create_or_update_from_tg_user(
        msg.from_user,
    )

    await msg.answer(
        'Кошельки, которые вы отслеживаете',
        reply_markup=await get_wallets_list_keyboard(client.pk),
    )


@router.callback_query(F.data == 'wallets_list')
async def to_wallets_list(query: CallbackQuery):
    await query.message.edit_text(
        'Кошельки, которые вы отслеживаете',
        reply_markup=await get_wallets_list_keyboard(query.message.chat.id),
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
async def edit(query: CallbackQuery, state: FSMContext):
    await state.set_state(WalletState.address)
    await query.message.answer('Введите адрес кошелька')


@router.callback_query(F.data == 'delete_wallet')
async def delete_wallet(query: CallbackQuery, state: FSMContext):
    await ClientWallet.objects.filter(
        wallet=await state.get_value('wallet_id'),
        client_id=query.message.chat.id,
    ).adelete()

    await query.message.edit_text(
        'Кошельки, которые вы отслеживаете',
        reply_markup=await get_wallets_list_keyboard(query.message.chat.id),
    )
