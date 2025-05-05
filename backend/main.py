import os

import django
from aiogram import F
from aiogram.enums import ChatType
from aiogram.types import BotCommand

from bot.loader import bot, dp, logger, loop


async def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()

    from bot.handlers import alerts, base, coin, filters, wallet
    from bot.middlewares import WithClientMiddleware
    from bot.notify import notify  # noqa

    dp.include_routers(
        base.router,
        wallet.router,
        coin.router,
        filters.router,
        alerts.router,
    )
    dp.message.filter(F.chat.type == ChatType.PRIVATE)
    dp.message.middleware(WithClientMiddleware())
    dp.callback_query.middleware(WithClientMiddleware())

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
                description='Редактировать отслеживаемые кошельки',
            ),
            BotCommand(
                command='/add_coin',
                description='Добавить монету для отслеживания',
            ),
            BotCommand(
                command='/edit_coin',
                description='Редактировать отслеживаемые монеты',
            ),
            BotCommand(
                command='/filters',
                description='Редактировать фильтры',
            ),
            BotCommand(
                command='/toggle_alerts',
                description='Вкл/выкл оповещения',
            ),
        ],
    )

    logger.info('Starting bot...')
    loop.create_task(notify())
    await dp.start_polling(bot)


if __name__ == '__main__':
    loop.run_until_complete(main())
