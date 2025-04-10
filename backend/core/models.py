from dataclasses import asdict

from aiogram import types
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from bot.gmgn import get_coin_info


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
    async def add_to_client(self, address: str, client_id: int) -> 'Wallet':
        wallet, _ = await self.aget_or_create(address=address)
        await ClientWallet.objects.acreate(
            client_id=client_id,
            wallet=wallet,
        )
        return wallet


class CoinManager(models.Manager):
    async def add_to_client(self, address: str, client_id: int) -> 'Coin':
        coin, _ = await self.aget_or_create(
            asdict(await get_coin_info(address, 'sol')),
            address=address,
        )
        await ClientCoin.objects.acreate(
            client_id=client_id,
            coin=coin,
        )
        return coin


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
    objects = WalletManager()

    class Meta:
        verbose_name = 'Кошелёк'
        verbose_name_plural = 'Кошельки'

    def __str__(self):
        return self.address


class Coin(models.Model):
    address = models.CharField('Адрес', max_length=255)
    name = models.CharField('Название', max_length=255, blank=True)
    symbol = models.CharField('Символ', max_length=255, blank=True)
    logo = models.URLField('Лого', blank=True)
    objects = CoinManager()

    class Meta:
        verbose_name = 'Монета'
        verbose_name_plural = 'Монеты'
        ordering = ['name']

    def __str__(self):
        return f'{self.symbol} ({self.name})'


class ClientWallet(models.Model):
    client = models.ForeignKey(Client, models.CASCADE, 'wallets')
    wallet = models.ForeignKey(Wallet, models.CASCADE, 'clients')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    objects: models.Manager

    class Meta:
        unique_together = ('client', 'wallet')


class CoinTrackingParams(models.TextChoices):
    PRICE_UP = 'price_up', 'Цена повышается'
    PRICE_DOWN = 'price_down', 'Цена понижается'


class ClientCoin(models.Model):
    client = models.ForeignKey(Client, models.CASCADE, 'coins')
    coin = models.ForeignKey(Coin, models.CASCADE, 'clients')
    tracking_param = models.CharField(
        'Параметр отслеживания',
        max_length=100,
        choices=CoinTrackingParams,
        blank=True,
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    objects: models.Manager

    class Meta:
        unique_together = ('client', 'coin')
