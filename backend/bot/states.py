from aiogram.fsm.state import State, StatesGroup


class WalletState(StatesGroup):
    address = State()
    chain = State()


class CoinState(StatesGroup):
    address = State()
    chain = State()
    tracking_price = State()


class FiltersState(StatesGroup):
    max_coin_price = State()
    min_coin_market_cap = State()
    max_coin_creation_date = State()
