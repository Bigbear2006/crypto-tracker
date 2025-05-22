from aiogram import types
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from bot.api.alchemy import AlchemyAPI, alchemy_chains
from bot.api.dexscreener import DexscreenerAPI
from bot.exceptions import WalletNotFound
from core.choices import CoinTrackingParams


class ClientManager(models.Manager):
    async def from_tg_user(self, user: types.User) -> 'Client':
        return await self.acreate(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            is_premium=user.is_premium or False,
        )

    async def update_from_tg_user(self, user: types.User) -> None:
        await self.filter(pk=user.id).aupdate(
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            is_premium=user.is_premium or False,
        )

    async def create_or_update_from_tg_user(
        self,
        user: types.User,
    ) -> tuple['Client', bool]:
        try:
            client = await self.aget(pk=user.id)
            await self.update_from_tg_user(user)
            await client.arefresh_from_db()
            return client, False
        except ObjectDoesNotExist:
            return await self.from_tg_user(user), True


class WalletManager(models.Manager):
    async def acreate(self, **kwargs):
        async with AlchemyAPI() as api:
            address = kwargs.get('address', '')
            if not await api.get_signatures(address):
                raise WalletNotFound(address=address)
        return await super().acreate(**kwargs)

    async def aget_or_create(self, address: str, chain: str):
        try:
            return await self.aget(address=address, chain=chain), False
        except ObjectDoesNotExist:
            return await self.acreate(address=address, chain=chain), True

    async def add_to_client(
        self,
        address: str,
        chain: str,
        client_id: int,
    ) -> 'Wallet':
        try:
            wallet = await self.aget(address=address, chain=chain)
        except ObjectDoesNotExist:
            wallet = await self.acreate(address=address, chain=chain)

        await ClientWallet.objects.acreate(
            client_id=client_id,
            wallet=wallet,
        )
        return wallet

    def get_tracked(self):
        return self.annotate(
            clients_count=models.Count(
                'clients',
                filter=models.Q(clients__client__alerts_enabled=True),
            ),
        ).filter(
            clients_count__gt=0,
        )


class CoinManager(models.Manager):
    async def aget_or_create(self, address: str, chain: str) -> 'Coin':
        try:
            coin = await self.aget(
                address=address,
                chain=alchemy_chains[chain],
            )
        except ObjectDoesNotExist:
            async with DexscreenerAPI() as api:
                coin_info = await api.get_coin_info(chain, address)
                coin = await self.acreate(
                    address=address,
                    chain=alchemy_chains[chain],
                    name=coin_info.name,
                    symbol=coin_info.symbol,
                    logo=coin_info.logo,
                    created_at=coin_info.created_at,
                )
        return coin

    async def add_to_client(
        self,
        address: str,
        chain: str,
        client_id: int,
    ) -> 'Coin':
        coin = await self.aget_or_create(address, chain)
        await ClientCoin.objects.acreate(
            client_id=client_id,
            coin=coin,
        )
        return coin

    async def update_client_coin(
        self,
        address: str,
        chain: str,
        *,
        client_id: int,
        coin_id: int,
    ) -> 'Coin':
        coin = await self.aget_or_create(address, chain)
        await ClientCoin.objects.filter(
            client_id=client_id,
            coin_id=coin_id,
        ).aupdate(
            coin=coin,
        )
        return coin

    def get_tracked(self):
        return self.annotate(clients_count=models.Count('clients')).filter(
            clients_count__gt=0,
        )


class User(AbstractUser):
    pass


class Client(models.Model):
    id = models.PositiveBigIntegerField(
        'Телеграм ID',
        primary_key=True,
    )
    first_name = models.CharField('Имя', max_length=255)
    last_name = models.CharField(
        'Фамилия',
        max_length=255,
        null=True,
        blank=True,
    )
    username = models.CharField(
        'Ник',
        max_length=32,
        null=True,
        blank=True,
    )
    is_premium = models.BooleanField(
        'Есть премиум',
        default=False,
    )
    alerts_enabled = models.BooleanField('Уведомления', default=True)
    max_coin_price = models.FloatField(
        'Максимальная цена монеты',
        null=True,
        blank=True,
    )
    min_coin_market_cap = models.PositiveBigIntegerField(
        'Минимальная капитализация монеты',
        null=True,
        blank=True,
    )
    # in minutes
    min_coin_age = models.IntegerField(
        'Минимальный возраст монеты',
        null=True,
        blank=True,
    )
    max_coin_age = models.IntegerField(
        'Максимальный возраст монеты',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    objects = ClientManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-created_at']

    def __str__(self):
        username = self.first_name
        if self.username:
            username += f' (@{self.username})'
        return username


class Wallet(models.Model):
    address = models.CharField('Адрес', max_length=255)
    chain = models.CharField('Блокчейн', max_length=255)
    objects = WalletManager()

    class Meta:
        verbose_name = 'Кошелёк'
        verbose_name_plural = 'Кошельки'
        ordering = ['address']

    def __str__(self):
        return f'{self.address[:20]}...'


class Coin(models.Model):
    address = models.CharField('Адрес', max_length=255)
    chain = models.CharField('Блокчейн', max_length=255)
    name = models.CharField('Название', max_length=255, blank=True)
    symbol = models.CharField('Символ', max_length=255, blank=True)
    logo = models.URLField('Лого', blank=True)
    created_at = models.DateTimeField('Дата создания монеты')
    objects = CoinManager()

    class Meta:
        verbose_name = 'Монета'
        verbose_name_plural = 'Монеты'
        ordering = ['symbol']

    def __str__(self):
        return self.symbol


class ClientWallet(models.Model):
    client = models.ForeignKey(
        Client,
        models.CASCADE,
        'wallets',
        verbose_name='Пользователь',
    )
    wallet = models.ForeignKey(
        Wallet,
        models.CASCADE,
        'clients',
        verbose_name='Кошелек',
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        unique_together = ('client', 'wallet')
        verbose_name = 'Отслеживаемый кошелек'
        verbose_name_plural = 'Отслеживаемые кошельки'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.client} - {self.wallet}'


class ClientCoin(models.Model):
    client = models.ForeignKey(
        Client,
        models.CASCADE,
        'coins',
        verbose_name='Пользователь',
    )
    coin = models.ForeignKey(
        Coin,
        models.CASCADE,
        'clients',
        verbose_name='Монета',
    )
    tracking_param = models.CharField(
        'Параметр отслеживания',
        max_length=100,
        choices=CoinTrackingParams,
        blank=True,
    )
    start_price = models.FloatField('Начальная цена', null=True, blank=True)
    percentage = models.IntegerField(
        'Отслеживаемое изменение цены в %',
        null=True,
        blank=True,
    )
    notification_sent = models.BooleanField(
        'Уведомление отправлено',
        default=False,
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        unique_together = ('client', 'coin')
        verbose_name = 'Отслеживаемая монета'
        verbose_name_plural = 'Отслеживаемые монеты'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.client} - {self.coin}'


class Transaction(models.Model):
    wallet = models.ForeignKey(
        Wallet,
        models.SET_NULL,
        'transactions',
        verbose_name='Кошелёк',
        null=True,
        blank=True,
    )
    coin = models.ForeignKey(
        Coin,
        models.SET_NULL,
        'transactions',
        verbose_name='Монета',
        null=True,
        blank=True,
    )
    coin_amount = models.FloatField(
        'Количество монет',
        null=True,
        blank=True,
    )
    coin_price = models.FloatField(
        'Цена токена',
        null=True,
        blank=True,
    )
    total_cost = models.FloatField(
        'Общая сумма',
        null=True,
        blank=True,
    )
    date = models.DateTimeField('Дата', max_length=255, null=True, blank=True)
    signature = models.CharField('Адрес транзакции', max_length=255)
    sent = models.BooleanField('Отправлена', default=False)

    def __str__(self):
        if not self.wallet or not self.coin:
            return self.signature
        return f'{self.wallet} - {self.coin}'

    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        ordering = ['-date']
