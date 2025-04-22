from dataclasses import dataclass


@dataclass
class CoinInfo:
    address: str
    symbol: str
    logo: str
    name: str
    market_cap: int
    price: float
    price_5m_percents: float | None = None

    @property
    def price_5m(self):
        return self.price + self.price * self.price_5m_percents


@dataclass
class Transaction:
    wallet_address: str
    token_address: str
    token_amount: int
    timestamp: int
    signature: str
