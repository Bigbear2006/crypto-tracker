from dataclasses import dataclass


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
    price: float
    price_1m: float


@dataclass
class WalletActivity:
    event_type: str
    cost_usd: float
    price_usd: float
    token: BaseCoinInfo
    token_amount: float
    timestamp: str
    tx_hash: str

    def to_text(self):
        return (
            f'Монета: {self.token.symbol}\n'
            f'Количество: {self.token_amount}\n'
            f'Цена: {self.price_usd}\n'
            f'Общая сумма покупки: {self.cost_usd}'
        )
