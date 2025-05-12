from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils.timezone import now
from django.utils.timezone import timedelta

from sbily.users.models import User
from sbily.utils.tasks import default_task_params
from sbily.utils.tasks import task_response

from .models import LinkClick

logger = get_task_logger(__name__)


@shared_task(**default_task_params("clean_up_analytics_data", acks_late=True))
def clean_up_analytics_data(self) -> dict:
    """Clean up analytics data as per user plan."""

    current_time = now()
    clicks = LinkClick.objects.filter(clicked_at__lte=current_time - timedelta(days=30))

    free_users_clicks = clicks.filter(link__user__role=User.ROLE_USER)
    premium_users_clicks = clicks.filter(
        link__user__role=User.ROLE_PREMIUM,
        clicked_at__lte=current_time - timedelta(days=365),
    )

    free_users_clicks_count, _ = free_users_clicks.delete()
    premium_users_clicks_count, _ = premium_users_clicks.delete()

    count = free_users_clicks_count + premium_users_clicks_count
    return task_response(
        "COMPLETED",
        f"A total of {count} analytics data were successfully removed.",
    )
