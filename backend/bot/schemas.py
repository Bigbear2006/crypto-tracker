from dataclasses import dataclass
from datetime import datetime


@dataclass
class CoinInfo:
    address: str
    symbol: str
    logo: str
    name: str
    created_at: datetime
    market_cap: int
    price: float
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
