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
class WalletActivity:
    cost_usd: str
    price_usd: str
    token: BaseCoinInfo
    token_amount: str
    timestamp: str

    def to_text(self):
        return f'Покупка {self.token_amount} монет {self.token.symbol} ' \
               f'по цене {self.price_usd} на общую сумму {self.cost_usd}'
