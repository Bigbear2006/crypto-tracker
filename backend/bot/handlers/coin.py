from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command('add_coin'))
async def add_coin(msg: Message):
    pass


@router.message(Command('track_coin'))
async def track_coin(msg: Message):
    pass


@router.message(Command('edit_coin'))
async def edit_coin(msg: Message):
    pass
