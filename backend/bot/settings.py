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

    WSOL_ADDRESS: str = field(
        default='So11111111111111111111111111111111111111112',
    )
    NOTIFY_TIMEOUT: int = field(default=30)
    PAGE_SIZE: int = field(default=5)
    DATE_FMT: str = field(default='%d.%m.%Y')


settings = Settings()
