from aiogram import F, Router, flags
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import alerts_kb
from core.models import Client

router = Router()


@router.message(Command('toggle_alerts'))
@flags.with_client
async def alerts(msg: Message, client: Client):
    alerts_status = 'включены' if client.alerts_enabled else 'выключены'
    await msg.answer(f'Оповещения {alerts_status}', reply_markup=alerts_kb)


@router.callback_query(F.data.in_(('enable_alerts', 'disable_alerts')))
async def toggle_alerts(query: CallbackQuery):
    alerts_enabled = query.data == 'enable_alerts'
    await Client.objects.filter(pk=query.message.chat.id).aupdate(
        alerts_enabled=alerts_enabled,
    )

    try:
        alerts_status = 'включены' if alerts_enabled else 'выключены'
        await query.message.edit_text(
            f'Оповещения {alerts_status}', reply_markup=alerts_kb,
        )
    except TelegramBadRequest:
        pass
