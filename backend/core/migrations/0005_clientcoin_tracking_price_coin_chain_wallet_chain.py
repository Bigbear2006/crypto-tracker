# Generated by Django 5.2 on 2025-04-10 17:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_clientcoin_tracking_param'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientcoin',
            name='tracking_price',
            field=models.FloatField(blank=True, null=True, verbose_name='Отслеживаемая цена'),
        ),
        migrations.AddField(
            model_name='coin',
            name='chain',
            field=models.CharField(default='sol', max_length=255, verbose_name='Блокчейн'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='wallet',
            name='chain',
            field=models.CharField(default='sol', max_length=255, verbose_name='Блокчейн'),
            preserve_default=False,
        ),
    ]
