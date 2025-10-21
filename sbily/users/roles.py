from enum import Enum

from django.utils.translation import gettext_lazy as _


class UserRole(str, Enum):
    """Enum for user roles."""

    ADMIN = "admin"
    USER = "user"
    PREMIUM = "premium"
    BUSINESS = "business"
    ADVANCED = "advanced"


ROLE_CHOICES = [
    (UserRole.ADMIN.value, _("Admin")),
    (UserRole.USER.value, _("User")),
    (UserRole.PREMIUM.value, _("Premium")),
    (UserRole.BUSINESS.value, _("Business")),
    (UserRole.ADVANCED.value, _("Advanced")),
]


class UserLinkLimit(str, Enum):
    """Enum for user roles with link limits."""

    USER = 10
    PREMIUM = 25
    BUSINESS = 50
    ADVANCED = 100


class LinkLimitMapping:
    """Mapping of user roles to their link limits."""

    ROLE_TO_LIMIT = {
        UserRole.USER.value: UserLinkLimit.USER.value,
        UserRole.PREMIUM.value: UserLinkLimit.PREMIUM.value,
        UserRole.BUSINESS.value: UserLinkLimit.BUSINESS.value,
        UserRole.ADVANCED.value: UserLinkLimit.ADVANCED.value,
    }
