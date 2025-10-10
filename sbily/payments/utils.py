from enum import Enum
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils.timezone import now
from django.utils.timezone import timedelta

from sbily.users.models import User
from sbily.utils.errors import bad_request_error

if TYPE_CHECKING:
    from collections.abc import Callable

    from .models import Subscription


class PlanType(str, Enum):
    """Enum for available plan types."""

    PREMIUM = User.ROLE_PREMIUM
    BUSINESS = User.ROLE_BUSINESS
    ADVANCED = User.ROLE_ADVANCED


class PlanCycle(str, Enum):
    """Enum for available billing cycles."""

    MONTHLY = "monthly"
    YEARLY = "yearly"


def is_upgrade(current_plan: str, new_plan: str) -> bool:
    """Check if the new plan is an upgrade from the current plan."""
    plan_hierarchy = {
        PlanType.PREMIUM: 1,
        PlanType.BUSINESS: 2,
        PlanType.ADVANCED: 3,
    }

    try:
        current_level = plan_hierarchy[PlanType(current_plan)]
        new_level = plan_hierarchy[PlanType(new_plan)]
    except ValueError:
        return False

    return new_level > current_level


def current_cycle_is_yearly(user: User) -> bool:
    if not user.subscription_active:
        return False

    sub: Subscription = user.subscription
    return (sub.end_date - sub.start_date) > timedelta(days=40)


def one_month_left_until_plan_end(user: User) -> bool:
    if not user.subscription_active:
        return False

    sub: Subscription = user.subscription
    return (sub.end_date - now()) < timedelta(days=31)


def calculate_unused_time_discount(user: User, new_plan: str = PlanType.PREMIUM.value):
    if not is_upgrade(user.user_level, new_plan):
        return False

    if not current_cycle_is_yearly(user) or one_month_left_until_plan_end(user):
        return False

    sub: Subscription = user.subscription
    sub_current_price = sub.price

    time_until_plan_end = sub.end_date - now()
    days_until_plan_end = time_until_plan_end.days
    unused_percent = round((days_until_plan_end * 100) / 365)

    return round((unused_percent * sub_current_price) / 100)


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
        PlanType.BUSINESS: lambda user: user.is_business,
        PlanType.ADVANCED: lambda user: user.is_advanced,
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
        PlanType.BUSINESS: {
            PlanCycle.MONTHLY: settings.STRIPE_BUSINESS_MONTHLY_PRICE_ID,
            PlanCycle.YEARLY: settings.STRIPE_BUSINESS_YEARLY_PRICE_ID,
        },
        PlanType.ADVANCED: {
            PlanCycle.MONTHLY: settings.STRIPE_ADVANCED_MONTHLY_PRICE_ID,
            PlanCycle.YEARLY: settings.STRIPE_ADVANCED_YEARLY_PRICE_ID,
        },
    }

    try:
        return stripe_prices[plan_type][cycle_type]
    except KeyError:
        return None
