from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.utils import get_paginated_keyboard, one_button_keyboard
from core.models import Coin, CoinTrackingParams, Wallet

cancel_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Отменить', callback_data='cancel')],
    ],
)

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
                callback_data='set_coin_percentage',
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

filters_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Максимальная цена монеты',
                callback_data='filter:max_coin_price',
            ),
        ],
        [
            InlineKeyboardButton(
                text='Минимальная капитализация монеты',
                callback_data='filter:min_coin_market_cap',
            ),
        ],
        [
            InlineKeyboardButton(
                text='Минимальный возраст монеты',
                callback_data='filter:min_coin_age',
            ),
        ],
        [
            InlineKeyboardButton(
                text='Максимальный возраст монеты',
                callback_data='filter:max_coin_age',
            ),
        ],
    ],
)

to_filters_kb = one_button_keyboard(text='Назад', callback_data='to_filters')

chains_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='SOL',
                callback_data='chain_solana',
            ),
            InlineKeyboardButton(
                text='ETH',
                callback_data='chain_ethereum',
            ),
        ],
        [
            InlineKeyboardButton(
                text='Base',
                callback_data='chain_base',
            ),
            InlineKeyboardButton(
                text='Blast',
                callback_data='chain_blast',
            ),
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
