from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command('toggle_alerts'))
async def toggle_alerts(msg: Message):
    pass
