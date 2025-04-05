from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.loader import logger
from core.models import Client

router = Router()


@router.message(Command('start'))
async def start(msg: Message):
    client, created = await Client.objects.create_or_update_from_tg_user(
        msg.from_user,
    )
    if created:
        logger.info(f'New client {client} id={client.pk} was created')
    else:
        logger.info(f'Client {client} id={client.pk} was updated')

    await msg.answer(f'Привет, {msg.from_user.full_name}!')
