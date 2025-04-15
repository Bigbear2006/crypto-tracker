from aiogram.fsm.state import State, StatesGroup


class WalletState(StatesGroup):
    address = State()
    chain = State()


class CoinState(StatesGroup):
    address = State()
    chain = State()
    tracking_price = State()
