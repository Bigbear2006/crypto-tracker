import os

import django
from aiogram import F
from aiogram.enums import ChatType
from aiogram.types import BotCommand

from bot.loader import bot, dp, logger, loop
from bot.notify import notify


async def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()

    from bot.handlers import alerts, coin, commands, wallet
    from bot.middlewares import WithClientMiddleware

    dp.include_routers(
        commands.router,
        wallet.router,
        coin.router,
        alerts.router,
    )
    dp.message.filter(F.chat.type == ChatType.PRIVATE)
    dp.message.middleware(WithClientMiddleware())

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(
        [
            BotCommand(command='/start', description='Запустить бота'),
            BotCommand(
                command='/add_wallet',
                description='Добавить кошелек для отслеживания',
            ),
            BotCommand(
                command='/edit_wallet',
                description='Редактировать отслеживаемый кошелек',
            ),
            BotCommand(
                command='/add_coin',
                description='Добавить монету для отслеживания',
            ),
            BotCommand(
                command='/edit_coin',
                description='Редактирование отслеживаемой монеты',
            ),
            BotCommand(
                command='/toggle_alerts',
                description='Вкл/выкл. оповещения',
            ),
        ],
    )

    logger.info('Starting bot...')
    loop.create_task(notify())
    await dp.start_polling(bot)


if __name__ == '__main__':
    loop.run_until_complete(main())
