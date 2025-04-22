import json

from aiohttp import ClientSession

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
        limit: int = 10,
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
            print(json.dumps(data, indent=2))
            return [
                i['signature']
                for i in data['result']
                if i['confirmationStatus'] == 'finalized'
            ]

    async def get_transaction(
        self,
        wallet_address: str,
        signature: str,
    ) -> Transaction:
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
            print(json.dumps(data, indent=2))
            meta = data['result']['meta']

            pre_token_balance = [
                i['owner']
                for i in meta['preTokenBalances']
                if i['owner'] == wallet_address
            ][0]

            post_token_balance = [
                i['owner']
                for i in meta['postTokenBalances']
                if i['owner'] == wallet_address
            ][0]

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
