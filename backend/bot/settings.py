from dataclasses import dataclass, field

from environs import Env

env = Env()
env.read_env()


def load_gmgn_cookie() -> str:
    try:
        with open('cookie.txt') as f:
            cookie = f.read()
    except FileNotFoundError:
        with open('cookie.txt', 'w'):
            cookie = ''
    return cookie


@dataclass
class Settings:
    BOT_TOKEN: str = field(default_factory=lambda: env('BOT_TOKEN'))
    REDIS_URL: str = field(default_factory=lambda: env('REDIS_URL'))

    GMGN_API_URL: str = field(default='https://gmgn.ai/api/v1/')
    GMGN_COOKIE: str = field(default_factory=load_gmgn_cookie)

    MIN_BUYING_AMOUNT: int = field(default=1000)
    MIN_COIN_MKT_CAP: int = field(default=100_000)
    MAX_COIN_PRICE: int = field(default=0.00018)

    PAGE_SIZE: int = field(default=5)


settings = Settings()
