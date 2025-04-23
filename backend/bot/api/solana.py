import asyncio

from aiohttp import ClientSession

from bot.loader import logger
from bot.schemas import Transaction


class SolanaAPI:
    def __init__(self, **session_kwargs):
        self.session = ClientSession(
            'https://api.mainnet-beta.solana.com/',
            **session_kwargs,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def get_signatures(
        self,
        address: str,
        *,
        limit: int = 5,
    ) -> list[str]:
        async with self.session.post(
            '',
            json={
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'getSignaturesForAddress',
                'params': [
                    address,
                    {'limit': limit},
                ],
            },
        ) as rsp:
            data = await rsp.json()
            logger.debug(data)

            if rsp.status == 429:
                retry_after = int(rsp.headers['Retry-After'])
                logger.debug(f'Sleep {retry_after} seconds...')
                await asyncio.sleep(retry_after)
                await self.get_signatures(address, limit=limit)

            if err := data.get('error'):
                logger.info(f'Error {err}')
                return []

            return [
                i['signature']
                for i in data['result']
                if i['confirmationStatus'] == 'finalized'
                if i['blockTime'] > 1745392842  # skip old transactions
            ]

    async def get_transaction(
        self,
        wallet_address: str,
        signature: str,
    ) -> Transaction | None:
        async with self.session.post(
            '',
            json={
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'getTransaction',
                'params': [
                    signature,
                ],
            },
        ) as rsp:
            data = await rsp.json()
            logger.debug(data)

            if rsp.status == 429:
                retry_after = int(rsp.headers['Retry-After'])
                logger.debug(f'Sleep {retry_after} seconds...')
                await asyncio.sleep(retry_after)
                await self.get_transaction(wallet_address, signature)

            if err := data.get('error'):
                logger.info(f'Error {err}')
                return

            try:
                meta = data['result']['meta']
                pre_token_balance = [
                    i
                    for i in meta['preTokenBalances']
                    if i['owner'] == wallet_address
                ][0]

                post_token_balance = [
                    i
                    for i in meta['postTokenBalances']
                    if i['owner'] == wallet_address
                ][0]
            except IndexError:
                return

            token_amount = (
                post_token_balance['uiTokenAmount']['uiAmount']
                - pre_token_balance['uiTokenAmount']['uiAmount']
            )

            return Transaction(
                wallet_address=wallet_address,
                token_address=pre_token_balance['mint'],
                token_amount=token_amount,
                timestamp=data['result']['blockTime'],
                signature=signature,
            )
