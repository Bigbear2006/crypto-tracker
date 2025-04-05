from aiogram import Router, flags
from aiogram.filters import Command
from aiogram.types import Message

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

    await msg.answer(f'Привет, {msg.from_user.full_name}!')
