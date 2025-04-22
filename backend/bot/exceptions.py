class NotFound(Exception):
    def __init__(self, address: str, object_name: str):
        self.address = address
        self.object_name = object_name
        super().__init__(f'{self.object_name} {self.address} not found')

    def __str__(self):
        return f'{self.object_name} {self.address} not found'


class CoinNotFound(NotFound):
    def __init__(self, address: str):
        super().__init__(address, 'Coin')


class WalletNotFound(Exception):
    def __init__(self, address: str):
        super().__init__(address, 'Wallet')
