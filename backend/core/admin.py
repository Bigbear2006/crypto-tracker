from django.contrib import admin

from core import models

admin.site.register(models.Client)
admin.site.register(models.Wallet)
admin.site.register(models.Coin)
