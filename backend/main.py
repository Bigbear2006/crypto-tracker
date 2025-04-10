import os

import django
from aiogram import F
from aiogram.enums import ChatType
from aiogram.types import BotCommand

from bot.loader import bot, dp, logger, loop


async def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()

    # print(
    #     await gmgn.get_coins_info(
    #         ['EQ8XnCvwZvhdJZZZeJeRv5bYyNTz5vQ4TL9VFxwCPcZc'], 'sol'
    #     )
    # )
    # print(
    #     await gmgn.get_wallet_activity(
    #         'DvFtsNc6qUsRKC5vZB6tBoVXKG3exHJdgutMuamXQAeS',
    #         'sol',
    #     ),
    # )

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
                command='/track_coin',
                description='Установить параметры отслеживания',
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
    await dp.start_polling(bot)


if __name__ == '__main__':
    loop.run_until_complete(main())
