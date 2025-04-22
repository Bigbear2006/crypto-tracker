from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.utils import get_paginated_keyboard
from core.models import Coin, CoinTrackingParams, Wallet

wallet_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Редактировать',
                callback_data='edit_wallet',
            ),
            InlineKeyboardButton(
                text='Удалить',
                callback_data='delete_wallet',
            ),
        ],
        [
            InlineKeyboardButton(
                text='Назад',
                callback_data='wallets_list',
            ),
        ],
    ],
)

coin_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Редактировать',
                callback_data='edit_coin',
            ),
            InlineKeyboardButton(
                text='Удалить',
                callback_data='delete_coin',
            ),
        ],
        [
            InlineKeyboardButton(
                text='Параметры отслеживания',
                callback_data='set_coin_tracking_params',
            ),
        ],
        [
            InlineKeyboardButton(
                text='Отслеживаемая цена',
                callback_data='set_coin_tracking_price',
            ),
        ],
        [
            InlineKeyboardButton(
                text='Назад',
                callback_data='coins_list',
            ),
        ],
    ],
)

alerts_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Вкл.',
                callback_data='enable_alerts',
            ),
            InlineKeyboardButton(
                text='Выкл.',
                callback_data='disable_alerts',
            ),
        ],
    ],
)

chains_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text='SOL', callback_data='chain_solana'),
            InlineKeyboardButton(text='ETH', callback_data='chain_ethereum'),
            InlineKeyboardButton(text='Base', callback_data='chain_base'),
        ],
        [
            InlineKeyboardButton(text='BSC', callback_data='chain_bsc'),
            InlineKeyboardButton(text='Tron', callback_data='chain_tron'),
            InlineKeyboardButton(text='Blast', callback_data='chain_blast'),
        ],
    ],
)


async def get_wallets_list_keyboard(client_id: int, *, page: int = 1):
    return await get_paginated_keyboard(
        Wallet,
        filters={'clients__client': client_id},
        prefix='wallet',
        page=page,
    )


async def get_coins_list_keyboard(client_id: int, *, page: int = 1):
    return await get_paginated_keyboard(
        Coin,
        filters={'clients__client': client_id},
        prefix='coin',
        page=page,
        previous_button_data='coin_previous',
        next_button_data='coins_next',
    )


async def get_coin_tracking_params_kb(*, back_button_data: str = None):
    kb = InlineKeyboardBuilder()
    for value, label in CoinTrackingParams.choices:
        kb.button(text=label, callback_data=value)
    if back_button_data:
        kb.button(text='Назад', callback_data=back_button_data)
    return kb.adjust(1).as_markup()
