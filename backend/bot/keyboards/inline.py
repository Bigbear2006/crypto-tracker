from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from django.db.models import Model, QuerySet

from bot.settings import settings
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


async def get_pagination_buttons(
    previous_button_data: str = None,
    next_button_data: str = None,
) -> list[InlineKeyboardButton]:
    pagination_buttons = []

    if previous_button_data:
        pagination_buttons.append(
            InlineKeyboardButton(
                text='<<',
                callback_data=previous_button_data,
            ),
        )

    if next_button_data:
        pagination_buttons.append(
            InlineKeyboardButton(text='>>', callback_data=next_button_data),
        )

    return pagination_buttons


async def keyboard_from_queryset(
    queryset: QuerySet,
    *,
    prefix: str,
    back_button_data: str = None,
    previous_button_data: str = None,
    next_button_data: str = None,
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    if back_button_data:
        kb.button(text='Назад', callback_data=back_button_data)

    async for obj in queryset:
        kb.button(text=str(obj), callback_data=f'{prefix}_{obj.pk}')

    kb.adjust(1)
    kb.row(
        *await get_pagination_buttons(
            previous_button_data,
            next_button_data,
        ),
    )
    return kb.as_markup()


async def get_paginated_keyboard(
    model: type[Model],
    *,
    filters: dict = None,
    page: int = 1,
    prefix: str = '',
    back_button_data: str = None,
    previous_button_data: str = 'catalog_previous',
    next_button_data: str = 'catalog_next',
) -> InlineKeyboardMarkup:
    if not filters:
        filters = {}

    total_count = await model.objects.filter(**filters).acount()
    total_pages = (total_count + settings.PAGE_SIZE - 1) // settings.PAGE_SIZE
    start, end = (page - 1) * settings.PAGE_SIZE, page * settings.PAGE_SIZE
    queryset = model.objects.filter(**filters)[start:end]

    return await keyboard_from_queryset(
        queryset,
        prefix=prefix,
        back_button_data=back_button_data,
        previous_button_data=previous_button_data if page > 1 else None,
        next_button_data=next_button_data if page < total_pages else None,
    )


async def get_wallets_list_keyboard(client_id: int):
    return await get_paginated_keyboard(
        Wallet,
        filters={'clients__client': client_id},
        prefix='wallet',
    )


async def get_coins_list_keyboard(client_id: int):
    return await get_paginated_keyboard(
        Coin,
        filters={'clients__client': client_id},
        prefix='coin',
    )


async def get_coin_tracking_params_kb():
    kb = InlineKeyboardBuilder()
    for value, label in CoinTrackingParams.choices:
        kb.button(text=label, callback_data=value)
    return kb.adjust(1).as_markup()
