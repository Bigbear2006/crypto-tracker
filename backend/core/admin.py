from django.contrib import admin
from django.contrib.auth.models import Group

from core import models

admin.site.unregister(Group)

admin.site.register(models.Client)
admin.site.register(models.Wallet)
admin.site.register(models.Coin)


@admin.register(models.ClientCoin)
class ClientCoinAdmin(admin.ModelAdmin):
    list_select_related = ('client', 'coin')


@admin.register(models.ClientWallet)
class ClientWalletAdmin(admin.ModelAdmin):
    list_select_related = ('client', 'wallet')


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_select_related = ('wallet', 'coin')
    readonly_fields = ('date', 'signature')
