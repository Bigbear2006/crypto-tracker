from django.contrib import admin
from django.contrib.auth.models import Group

from core import models

admin.site.unregister(Group)

admin.site.register(models.Client)
admin.site.register(models.Wallet)


class CoinFilter(admin.SimpleListFilter):
    title = 'Наличие монеты'
    parameter_name = 'coin_null'

    def lookups(self, request, model_admin):
        return (
            ('has', 'С монетой'),
            ('null', 'Без монеты'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'has':
            return queryset.filter(coin__isnull=False)
        if self.value() == 'null':
            return queryset.filter(coin__isnull=True)
        return queryset


@admin.register(models.Coin)
class CoinAdmin(admin.ModelAdmin):
    search_fields = ('address',)


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
    list_filter = ('sent', CoinFilter)
