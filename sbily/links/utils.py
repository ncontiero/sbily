from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from sbily.users.models import User


def validate_link_creation(is_temporary: bool, user: User) -> None:  # noqa: FBT001
    """Helper function to validate link creation permissions.

    Args:
        is_temporary: Whether the link being created is temporary.
        user: User instance to validate permissions for.

    Raises:
        ValidationError: If user lacks required permissions.
    """

    error_message = _(
        "You have reached the maximum number of links allowed for your account. "
        "If you want to create more links, you can buy more links in your account settings."  # noqa: E501
        if user.is_premium
        else "Please upgrade your account to create more links.",
    )
    if (is_temporary and not user.can_create_temporary_link()) or (
        not is_temporary and not user.can_create_link()
    ):
        error_code = "max_links_reached"
        raise ValidationError(error_message, code=error_code)


def user_can_create_link(
    link_id: int | None,
    link_remove_at: datetime | None,
    user: User,
) -> None:
    """Checks if the user can create a new link or modify an existing link's temporary
    status according to their account permissions.

    Args:
        link_id: ID of existing link to modify, or None for new link.
        link_remove_at: Removal datetime for temporary link, or None for permanent link.
        user: User attempting to create/modify the link.

    Raises:
        ValidationError: If the user has reached the maximum number of links allowed
        for their account.
    """
    if not link_id:
        validate_link_creation(is_temporary=bool(link_remove_at), user=user)
        return

    try:
        link = user.shortened_links.get(id=link_id)
    except User.shortened_links.model.DoesNotExist:
        validate_link_creation(is_temporary=bool(link_remove_at), user=user)
        return

    # Skip validation if temporary status is not changing
    is_temporary_status_changed = bool(link_remove_at) != bool(link.remove_at)
    if is_temporary_status_changed:
        validate_link_creation(is_temporary=bool(link_remove_at), user=user)
