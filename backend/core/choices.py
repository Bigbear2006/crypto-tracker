from django.db import models


class CoinTrackingParams(models.TextChoices):
    PRICE_UP = 'price_up', 'Цена повышается'
    PRICE_DOWN = 'price_down', 'Цена понижается'
