from enum import Enum
from typing import TYPE_CHECKING

from django.conf import settings

from sbily.users.models import User
from sbily.utils.errors import bad_request_error

if TYPE_CHECKING:
    from collections.abc import Callable


class PlanType(str, Enum):
    """Enum for available plan types."""

    PREMIUM = User.ROLE_PREMIUM


class PlanCycle(str, Enum):
    """Enum for available billing cycles."""

    MONTHLY = "monthly"
    YEARLY = "yearly"


def validate_plan_selection(plan: str, plan_cycle: str, user: User):
    try:
        plan_type = PlanType(plan)
    except ValueError:
        bad_request_error("Invalid plan selected")

    try:
        PlanCycle(plan_cycle)
    except ValueError:
        bad_request_error("Invalid plan cycle selected")

    plan_check_map: dict[PlanType, Callable[[User], bool]] = {
        PlanType.PREMIUM: lambda user: user.is_premium,
    }

    check_method = plan_check_map.get(plan_type)
    if check_method and check_method(user):
        bad_request_error("You already have this plan")


def get_stripe_price(plan: str, plan_cycle: str) -> str | None:
    """Get the Stripe price ID for the given plan and cycle."""
    try:
        plan_type = PlanType(plan)
        cycle_type = PlanCycle(plan_cycle)
    except ValueError:
        return None

    stripe_prices: dict[PlanType, dict[PlanCycle, str]] = {
        PlanType.PREMIUM: {
            PlanCycle.MONTHLY: settings.STRIPE_PREMIUM_MONTHLY_PRICE_ID,
            PlanCycle.YEARLY: settings.STRIPE_PREMIUM_YEARLY_PRICE_ID,
        },
    }

    try:
        return stripe_prices[plan_type][cycle_type]
    except KeyError:
        return None


# def is_upgrade_plan(plan: str, user: User) -> bool:
#     """
#     Check if the selected plan is an upgrade for the user.
#     Order: Premium -> Business -> Advanced

#     Returns: True if the plan is an upgrade, False otherwise.
#     """
#     try:
#         plan_type = PlanType(plan)
#     except ValueError:
#         return False

#     plan_order = {
#         PlanType.PREMIUM: 0,
#         PlanType.BUSINESS: 1,
#         PlanType.ADVANCED: 2,
#     }

#     return plan_order[plan_type] > plan_order.get(user.role, -1)
