from aiogram.fsm.state import State, StatesGroup


class WalletState(StatesGroup):
    address = State()
    chain = State()


class CoinState(StatesGroup):
    address = State()
    chain = State()
    percentage = State()


class FiltersState(StatesGroup):
    max_coin_price = State()
    min_coin_market_cap = State()
    min_coin_age = State()
    max_coin_age = State()


class SearchState(StatesGroup):
    min_liquidity = State()
    extra_filters = State()
