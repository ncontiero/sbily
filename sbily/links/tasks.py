from collections import defaultdict

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.timezone import now

from sbily.notifications.models import Notification
from sbily.users.models import User
from sbily.utils.tasks import default_task_params
from sbily.utils.tasks import task_response

from .models import ShortenedLink

SITE_BASE_URL = settings.BASE_URL or ""


def send_notification_deleted_links(
    user: User,
    links: list[ShortenedLink],
    **kwargs,
) -> None:
    """
    Send a notification to the user when their links have been deleted.

    Args:
        user: The user to notify.
        links: List of deleted links.
        **kwargs: Additional context data.
    """
    context = kwargs.copy()
    context["links"] = links
    context.setdefault("links_count", len(links))

    content = render_to_string("notifications/links/links_deleted.md", context)

    Notification.objects.create(
        title="Your links have been deleted!",
        user=user,
        content=content,
    )


@shared_task(**default_task_params("delete_expired_links", acks_late=True))
def delete_expired_links(self) -> dict:
    """Delete expired links from the database."""
    expired_links = ShortenedLink.objects.select_related("user").filter(
        remove_at__lte=now(),
    )
    expired_links_backup = list(expired_links)
    deleted_count = expired_links.delete()[0]

    if deleted_count > 0:
        user_links = defaultdict(list)
        for link in expired_links_backup:
            user_links[link.user].append(link)

        for user, links in user_links.items():
            send_notification_deleted_links(
                user=user,
                links=links,
            )
    return task_response(
        "COMPLETED",
        f"Deleted {deleted_count} expired links.",
        deleted_count=deleted_count,
    )


@shared_task(**default_task_params("delete_excess_user_links", acks_late=True))
def delete_excess_user_links(self) -> dict:
    """Delete excess links for users that have exceeded their link limit."""
    users = User.objects.prefetch_related("shortened_links").all()
    total_deleted_count = 0

    for user in users:
        links = user.shortened_links.order_by("-updated_at")
        excess_permalinks = user.permanent_links_used - user.max_num_links
        excess_temporary_links = (
            user.temporary_links_used - user.max_num_links_temporary
        )
        user_deleted_count = 0
        deleted_links = []

        if excess_permalinks > 0:
            links_to_delete = links.filter(remove_at__isnull=True)[:excess_permalinks]
            deleted_links.extend(list(links_to_delete))
            deleted = links.filter(pk__in=links_to_delete).delete()[0]
            user_deleted_count += deleted
            total_deleted_count += deleted

        if excess_temporary_links > 0:
            temp_links_to_delete = links.filter(remove_at__isnull=False)[
                :excess_temporary_links
            ]
            deleted_links.extend(list(temp_links_to_delete))
            deleted = links.filter(pk__in=temp_links_to_delete).delete()[0]
            user_deleted_count += deleted
            total_deleted_count += deleted

        if user_deleted_count > 0:
            send_notification_deleted_links(
                user=user,
                links=deleted_links,
                need_upgrade=True,
            )

    return task_response(
        "COMPLETED",
        f"Deleted {total_deleted_count} excess links for users.",
        deleted_count=total_deleted_count,
    )


@shared_task(**default_task_params("delete_link_by_id", acks_late=True))
def delete_link_by_id(self, link_id: int) -> dict:
    """Delete a link by its ID."""
    try:
        with transaction.atomic():
            link = ShortenedLink.objects.select_related("user").get(id=link_id)
            user = link.user
            link.delete()

            send_notification_deleted_links(
                user=user,
                links=[link],
            )

            return task_response(
                "COMPLETED",
                f"Successfully deleted link with ID {link_id}",
                deleted_count=1,
            )
    except ShortenedLink.DoesNotExist:
        return task_response(
            "FAILED",
            f"Link with ID {link_id} does not exist",
            deleted_count=0,
        )
