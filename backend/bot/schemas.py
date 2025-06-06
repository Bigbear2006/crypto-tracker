from dataclasses import dataclass
from datetime import datetime

from bot.text_utils import age_to_str


@dataclass
class BaseCoinInfo:
    address: str
    symbol: str
    logo: str
    name: str
    market_cap: int
    price: float


@dataclass
class CoinInfo(BaseCoinInfo):
    """For Dexscreener API"""

    pair_address: str
    created_at: datetime
    price_5m_percents: float | None = None

    @property
    def price_5m(self):
        if self.price_5m_percents is None:
            return self.price
        return self.price + self.price * self.price_5m_percents


@dataclass
class CoinInputData:
    network: str
    address: str

    @classmethod
    def from_network(cls, network: str, addresses: list[str]):
        return [cls(network, i) for i in addresses]


@dataclass
class CoinPrice:
    address: str
    chain: str
    price: float

    def __post_init__(self):
        self.price = float(self.price)


@dataclass
class HistoricalPrice:
    price: str
    timestamp: str
    market_cap: str


@dataclass
class CoinHistory:
    address: str
    chain: str
    prices: list[HistoricalPrice]

    @property
    def price(self):
        return float(self.prices[0].price)

    @property
    def price_5m(self):
        if len(self.prices) < 2:
            return None
        return float(self.prices[1].price)

    @property
    def price_5m_percents(self):
        if not self.price_5m:
            return None
        return (self.price - self.price_5m) / self.price_5m * 100

    @property
    def market_cap(self):
        return float(self.prices[0].market_cap)


@dataclass
class TransactionData:
    wallet_address: str
    token_address: str
    token_amount: float
    timestamp: int
    signature: str


@dataclass
class TokenListParams:
    sort_by: str = 'liquidity'
    sort_type: str = 'desc'
    offset: int = 0
    limit: int = 50
    min_liquidity: int = 100
    max_liquidity: int | None = None


@dataclass
class TokenInfo(BaseCoinInfo):
    """For BirdEye API"""

    liquidity: float
    age: int | None = None

    def __post_init__(self):
        if self.age:
            self.age = int(self.age)

    def __hash__(self):
        return hash(self.address)

    def __eq__(self, other):
        return self.address == other.address

    def __ne__(self, other):
        return self.address != other.address

    @property
    def message_text(self):
        return (
            f'{self.symbol}\n'
            f'Цена: {round(self.price, 2) if self.price > 5 else self.price}\n'
            f'Возраст: {age_to_str(self.age, round_big=True)}\n'
            f'Капитализация: {round(self.market_cap, 2)}\n'
            f'Ликвидность: {round(self.liquidity, 2)}\n'
        )


def exclude_none_dict_factory(data):
    return {k: v for k, v in data if v is not None}
