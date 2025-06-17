# ruff: noqa: PLC0415

import os

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("sbily")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)


# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    from sbily.links.tasks import clean_up_analytics_data
    from sbily.users.tasks import reset_user_monthly_link_limits

    sender.add_periodic_task(
        crontab(minute=0, hour=0),
        reset_user_monthly_link_limits.s(),
        name="Reset Users Monthly Link Limits",
    )
    sender.add_periodic_task(
        crontab(minute=0, hour=0),
        clean_up_analytics_data.s(),
        name="Clean Up Analytics Data",
    )
