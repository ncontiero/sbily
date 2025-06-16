from celery import shared_task
from django.utils.timezone import now
from django.utils.timezone import timedelta

from sbily.utils.tasks import default_task_params
from sbily.utils.tasks import task_response

from .models import LinkClick


@shared_task(**default_task_params("clean_up_analytics_data", acks_late=True))
def clean_up_analytics_data(self) -> dict:
    """Clean up analytics data."""

    current_time = now()
    five_year_ago = timedelta(days=365 * 5)  # 5 years in days

    # Delete LinkClick objects older than 5 years
    count, _ = LinkClick.objects.filter(
        created_at__lt=current_time - five_year_ago,
    ).delete()

    return task_response(
        "COMPLETED",
        f"A total of {count} analytics data were successfully removed.",
    )
