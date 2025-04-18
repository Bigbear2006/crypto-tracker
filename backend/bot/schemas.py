from dataclasses import dataclass
from enum import StrEnum


class EventType(StrEnum):
    buy = 'buy'
    sell = 'sell'


@dataclass
class BaseCoinInfo:
    address: str
    symbol: str
    logo: str


@dataclass
class CoinInfo(BaseCoinInfo):
    name: str


@dataclass
class CoinPrice:
    address: str
    price: str
    price_1m: str


@dataclass
class CoinMKTCap:
    address: str
    circulating_supply: str
    price: str

    @property
    def mkt_cap(self) -> float:
        return float(self.circulating_supply) * float(self.price)


@dataclass
class WalletActivity:
    event_type: EventType
    cost_usd: str
    price_usd: str
    token: BaseCoinInfo
    token_amount: str
    timestamp: str
    tx_hash: str

    def to_text(self):
        return (
            f'Монета: {self.token.symbol}\n'
            f'Количество: {self.token_amount}\n'
            f'Цена: {self.price_usd}\n'
            f'Общая сумма покупки: {self.cost_usd}'
        )
