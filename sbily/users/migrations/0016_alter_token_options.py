# Generated by Django 5.1.8 on 2025-04-17 22:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_user_card_last_four_digits_user_stripe_customer_id'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='token',
            options={'ordering': ['-created_at']},
        ),
    ]
