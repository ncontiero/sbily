from django.db.models import QuerySet
from django.utils import timezone

from sbily.links.models import LinkClick
from sbily.users.models import User


def filter_clicks_by_plan(clicks: QuerySet[LinkClick], user: User):
    """Filter clicks based on the user plan."""
    current_time = timezone.now()
    thirty_days = 30
    one_year = 365

    time_mapping = {
        User.ROLE_PREMIUM: one_year,
    }

    # Default to 30 days for free users
    time = time_mapping.get(user.role, thirty_days)

    return clicks.filter(clicked_at__gte=current_time - timezone.timedelta(days=time))


def get_user_clicks(user: User):
    """
    Retrieve all clicks for a given user.
    If the user has an active subscription, filter clicks based on the plan type.
    """

    clicks = LinkClick.objects.filter(link__user=user)
    return filter_clicks_by_plan(clicks, user)
