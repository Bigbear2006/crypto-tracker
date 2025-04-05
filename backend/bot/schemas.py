from dataclasses import dataclass


@dataclass
class CoinInfo:
    address: str
    symbol: str
    name: str
    logo: str
