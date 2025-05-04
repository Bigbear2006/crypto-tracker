from dataclasses import dataclass, field

from environs import Env

env = Env()
env.read_env()


@dataclass
class Settings:
    BOT_TOKEN: str = field(default_factory=lambda: env('BOT_TOKEN'))
    REDIS_URL: str = field(default_factory=lambda: env('REDIS_URL'))
    ALCHEMY_API_KEY: str = field(
        default_factory=lambda: env('ALCHEMY_API_KEY'),
    )

    MIN_BUYING_AMOUNT: int = field(default=1000)
    MIN_COIN_MARKET_CAP: int = field(default=100_000)
    MAX_COIN_PRICE: int = field(default=0.00018)

    NOTIFY_TIMEOUT: int = field(default=10)
    PAGE_SIZE: int = field(default=5)


settings = Settings()
