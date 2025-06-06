# Generated by Django 5.2 on 2025-05-03 12:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_txhash_alter_coin_options_alter_wallet_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('coin_amount', models.FloatField(verbose_name='Количество токенов')),
                ('coin_price', models.FloatField(verbose_name='Цена токена')),
                ('total_cost', models.FloatField(verbose_name='Общая сумма')),
                ('date', models.DateTimeField(max_length=255, verbose_name='Дата')),
                ('signature', models.CharField(max_length=255, verbose_name='Адрес транзакции')),
                ('sent', models.BooleanField(default=False, verbose_name='Отправлена')),
                ('coin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='core.coin', verbose_name='Адрес токена')),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='core.wallet', verbose_name='Адрес кошелька')),
            ],
            options={
                'verbose_name': 'Транзакция',
                'verbose_name_plural': 'Транзакции',
                'ordering': ['-date'],
            },
        ),
        migrations.DeleteModel(
            name='TxHash',
        ),
    ]
