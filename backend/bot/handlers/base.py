from aiogram import F, Router, flags
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.loader import logger
from core.models import Client

router = Router()


@router.message(Command('start'))
@flags.with_client
async def start(msg: Message, client: Client, client_created: bool):
    if client_created:
        logger.info(f'New client {client} id={client.pk} was created')
    else:
        logger.info(f'Client {client} id={client.pk} was updated')

    await msg.answer(
        f'Привет, {msg.from_user.full_name}!\n\n'
        f'Выбери одну из команд:\n'
        '/start - Запустить бота\n'
        '/add_wallet - Добавить кошелек для отслеживания\n'
        '/edit_wallet - Редактировать отслеживаемые кошельки\n'
        '/add_coin - Добавить монету для отслеживания\n'
        '/edit_coin - Редактировать отслеживаемые монеты\n'
        '/toggle_alerts - Вкл/выкл оповещения',
    )


@router.callback_query(F.data == 'cancel')
async def cancel(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.edit_text('Действие отменено')
