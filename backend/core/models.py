from typing import Optional

from aiogram import types
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, models
from django.utils.timezone import now

from bot.api.alchemy import AlchemyAPI, alchemy_chains
from bot.api.dexscreener import DexscreenerAPI
from bot.exceptions import WalletNotFound
from bot.schemas import CoinInfo
from bot.text_utils import age_to_str
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
    async def aget_or_create(
        self,
        address: str,
        chain: str,
        coin_info: CoinInfo | None = None,
    ) -> 'Coin':
        alchemy_chain = alchemy_chains[chain]
        try:
            return await self.aget(address=address, chain=alchemy_chain)
        except ObjectDoesNotExist:
            pass

        if not coin_info:
            async with DexscreenerAPI() as api:
                coin_info = await api.get_coin_info(chain, address)

        try:
            return await self.acreate(
                address=address,
                chain=alchemy_chain,
                name=coin_info.name,
                symbol=coin_info.symbol,
                logo=coin_info.logo,
                pair_address=coin_info.pair_address,
                created_at=coin_info.created_at,
            )
        except IntegrityError:
            return await self.aget(address=address, chain=alchemy_chain)

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


class ClientFiltersManager(models.Manager):
    async def get_by_id(self, pk: int | str) -> Optional['ClientFilters']:
        try:
            return await self.aget(pk=pk)
        except ObjectDoesNotExist:
            return

    async def update_by_id(self, pk: int | str, **kwargs):
        return await self.filter(pk=pk).aupdate(**kwargs)


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
    pair_address = models.CharField('Адрес пула', max_length=255)
    created_at = models.DateTimeField('Дата создания монеты')
    objects = CoinManager()

    class Meta:
        unique_together = ('address', 'chain')
        verbose_name = 'Монета'
        verbose_name_plural = 'Монеты'
        ordering = ['symbol']

    def __str__(self):
        return self.symbol

    @property
    def age(self):
        return (now() - self.created_at).total_seconds() / 60


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


class ClientFilters(models.Model):
    client = models.OneToOneField(Client, models.CASCADE, primary_key=True)
    min_liquidity = models.FloatField('Ликвидность')
    min_price = models.FloatField('Мин. цена', null=True, blank=True)
    max_price = models.FloatField('Макс. цена', null=True, blank=True)
    min_age = models.IntegerField('Мин. возраст', default=0)
    max_age = models.IntegerField('Мин. возраст', null=True, blank=True)
    min_market_cap = models.IntegerField('Капитализация', default=0)
    results = models.JSONField('Результаты')
    objects = ClientFiltersManager()

    class Meta:
        verbose_name = 'Фильтры пользователя'
        verbose_name_plural = 'Фильтры пользователей'

    def __str__(self):
        return str(self.client)

    @property
    def message_text(self):
        text = ''
        if self.min_liquidity:
            text += f'Ликвидность: {self.min_liquidity}\n'
        if self.min_price:
            text += f'Мин. цена: {self.min_price}\n'
        if self.max_price:
            text += f'Макс. цена: {self.max_price}\n'
        if self.min_age:
            text += f'Мин. возраст: {age_to_str(self.min_age)}\n'
        if self.max_age:
            text += f'Макс. возраст: {age_to_str(self.max_age)}\n'
        if self.min_market_cap:
            text += f'Капитализация: {self.min_market_cap}\n'
        return text
