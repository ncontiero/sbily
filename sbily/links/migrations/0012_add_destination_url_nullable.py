# Generated by Django 5.1.9 on 2025-05-11 01:29

import django.core.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('links', '0011_remove_shortenedlink_remove_at_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='shortenedlink',
            name='links_short_shorten_71809b_idx',
        ),
        migrations.AddField(
            model_name='shortenedlink',
            name='destination_url',
            field=models.URLField(blank=True, help_text='The destination URL that will be shortened', max_length=2000, verbose_name='Destination URL'),
        ),
        migrations.AddField(
            model_name='shortenedlink',
            name='shortened_path',
            field=models.CharField(blank=True, db_index=True, error_messages={'max_length': 'Shortened link must be at most 10 characters long', 'unique': 'This shortened link already exists'}, help_text='The shortened URL path', max_length=10, null=True, unique=True, validators=[django.core.validators.RegexValidator(message='Shortened link must be alphanumeric with hyphens and underscores only', regex='^[a-zA-Z0-9-_]*$')], verbose_name='Shortened path'),
        ),
        migrations.AddIndex(
            model_name='shortenedlink',
            index=models.Index(fields=['shortened_path', 'user'], name='links_short_shorten_7427c3_idx'),
        ),
    ]
