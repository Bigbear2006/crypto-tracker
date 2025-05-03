from aiohttp import ClientSession
from yarl import URL


class APIClient:
    def __init__(self, base_url: str | URL | None = None, **session_kwargs):
        self.session = ClientSession(
            base_url,
            **session_kwargs,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
