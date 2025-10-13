import logging
from datetime import datetime
from decimal import Decimal

import stripe
from django.db import models
from django.db import transaction
from django.utils.timezone import now
from django.utils.timezone import timedelta
from django.utils.translation import gettext_lazy as _

from sbily.users.models import User

from .utils import PlanCycle
from .utils import PlanType
from .utils import current_cycle_is_yearly
from .utils import get_stripe_price
from .utils import is_upgrade
from .utils import one_month_left_until_plan_end

logger = logging.getLogger("payments.models")


class Subscription(models.Model):
    LEVEL_PREMIUM = PlanType.PREMIUM.value
    LEVEL_BUSINESS = PlanType.BUSINESS.value
    LEVEL_ADVANCED = PlanType.ADVANCED.value

    STATUS_ACTIVE = "active"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"
    STATUS_INCOMPLETE = "incomplete"
    STATUS_PASTDUE = "past_due"

    LEVEL_CHOICES = [
        (LEVEL_PREMIUM, _("Premium")),
        (LEVEL_BUSINESS, _("Business")),
        (LEVEL_ADVANCED, _("Advanced")),
    ]

    STATUS_CHOICES = [
        (STATUS_ACTIVE, _("Active")),
        (STATUS_CANCELED, _("Canceled")),
        (STATUS_EXPIRED, _("Expired")),
        (STATUS_INCOMPLETE, _("Incomplete")),
        (STATUS_PASTDUE, _("Past Due")),
    ]

    level = models.CharField(
        _("level"),
        max_length=10,
        choices=LEVEL_CHOICES,
        default=LEVEL_PREMIUM,
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="subscription",
        verbose_name=_("user"),
    )
    stripe_subscription_id = models.CharField(
        _("Stripe subscription ID"),
        max_length=100,
        blank=True,
    )
    stripe_subscription_schedule_id = models.CharField(
        _("Stripe subscription schedule ID"),
        max_length=100,
        blank=True,
    )
    status = models.CharField(
        _("status"),
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_INCOMPLETE,
    )
    start_date = models.DateTimeField(_("start date"), default=now)
    end_date = models.DateTimeField(_("end date"), null=True, blank=True)
    is_auto_renew = models.BooleanField(_("auto renew"), default=True)
    price = models.DecimalField(
        _("price"),
        max_digits=6,
        decimal_places=2,
        default=10.00,
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"

    @transaction.atomic
    def save(self, *args, **kwargs):
        if (
            not self.pk
            or self._state.adding
            or (self.status == self.STATUS_ACTIVE and not self.end_date)
        ):
            self.end_date = now() + timedelta(days=30)

        if self.status == self.STATUS_ACTIVE and (
            not self.pk or self._state.adding or self._status_changed()
        ):
            self.user.choose_plan(self.level)

        if (
            self.status in [self.STATUS_CANCELED, self.STATUS_EXPIRED]
            and self._status_changed()
        ):
            self.user.downgrade_to_free()

        super().save(*args, **kwargs)

    @property
    def cycle(self):
        """Return the cycle of the subscription"""
        is_yearly_cycle = (self.end_date - self.start_date) > timedelta(days=35)
        return PlanCycle.YEARLY.value if is_yearly_cycle else PlanCycle.MONTHLY.value

    def _status_changed(self):
        """Check if the status has changed"""
        if not self.pk:
            return True

        try:
            old_instance = Subscription.objects.get(pk=self.pk)
        except Subscription.DoesNotExist:
            return True
        else:
            return old_instance.status != self.status

    def is_active(self):
        """Check if the subscription is active"""
        return (
            self.status == self.STATUS_ACTIVE
            and self.end_date
            and self.end_date > now()
        )

    def cancel(self):
        """Cancel subscription"""
        self.status = self.STATUS_CANCELED
        self.is_auto_renew = False
        self.save()

    def renew(self):
        """Renew subscription"""
        self.status = self.STATUS_ACTIVE
        self.end_date = now() + timedelta(days=30)
        self.is_auto_renew = True
        self.save()

    @classmethod
    @transaction.atomic
    def create_subscription(
        cls,
        user: User,
        payment_method_id=None,
        plan: str = PlanType.PREMIUM,
        plan_cycle: str = PlanCycle.MONTHLY,
    ):
        """Create a subscription"""

        customer = user.get_stripe_customer()
        try:
            user.update_card_details(payment_method_id)

            price = get_stripe_price(plan, plan_cycle)
            if not price:
                return {"status": "error", "error": "Invalid plan or cycle"}

            is_monthly = plan_cycle == PlanCycle.MONTHLY
            sub, _ = cls.objects.get_or_create(
                user=user,
                defaults={
                    "level": plan,
                    "price": Decimal("10.00"),
                    "status": cls.STATUS_INCOMPLETE,
                    "start_date": now(),
                    "end_date": now() + timedelta(days=30 if is_monthly else 365),
                    "is_auto_renew": True,
                },
            )

            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price}],
                metadata={"user_id": user.id, "plan": plan},
                expand=["latest_invoice.payments"],
            )

            sub.stripe_subscription_id = subscription.id
            sub.stripe_subscription_schedule_id = subscription.schedule or ""
            stripe_sub_data = subscription.get("items", {}).data[0]
            sub.price = Decimal(stripe_sub_data.plan.amount or 0) / 100
            sub.level = plan
            sub.is_auto_renew = subscription.cancel_at_period_end is False

            payments = subscription.latest_invoice.payments.data
            payment_intent = stripe.PaymentIntent.retrieve(
                payments[0].payment.payment_intent,
            )

            if subscription.status == "active":
                sub.status = cls.STATUS_ACTIVE
            elif subscription.status == "incomplete":
                sub.status = cls.STATUS_INCOMPLETE
            elif subscription.status == "past_due":
                sub.status = cls.STATUS_PASTDUE
                sub.is_auto_renew = False

            sub.save()

            if payment_intent and payment_intent.status == "requires_action":
                return {
                    "status": "action_required",
                    "client_secret": payment_intent.client_secret,
                    "subscription": sub,
                }
        except stripe.StripeError as e:
            if hasattr(sub, "pk") and sub.pk:
                sub.status = cls.STATUS_INCOMPLETE
                sub.save()

            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success", "subscription": sub}

    def downgrade_or_change_cycle(
        self,
        price: str,
        current_period_end: int,
        new_plan: str = PlanType.PREMIUM.value,
        new_plan_cycle: str = PlanCycle.MONTHLY.value,
    ):
        if self.stripe_subscription_schedule_id:
            stripe.SubscriptionSchedule.release(
                self.stripe_subscription_schedule_id,
            )

        stripe.Subscription.modify(
            self.stripe_subscription_id,
            cancel_at_period_end=True,
        )
        stripe_sub_sched = stripe.SubscriptionSchedule.create(
            customer=self.user.stripe_customer_id,
            start_date=current_period_end,
            end_behavior="release",
            phases=[
                {
                    "items": [{"price": price, "quantity": 1}],
                    "proration_behavior": "always_invoice",
                    "metadata": {"plan": new_plan},
                    "duration": {
                        "interval": "month"
                        if new_plan_cycle == PlanCycle.MONTHLY
                        else "year",
                        "interval_count": 1,
                    },
                },
            ],
        )

        self.stripe_subscription_schedule_id = stripe_sub_sched.id
        self.save(update_fields=["stripe_subscription_schedule_id"])
        return {"status": "success", "subscription": self}

    @classmethod
    @transaction.atomic
    def change_subscription(  # noqa: C901
        cls,
        user: User,
        payment_method_id=None,
        new_plan: str = PlanType.PREMIUM,
        new_plan_cycle: str = PlanCycle.MONTHLY,
    ):
        """Change a subscription"""
        try:
            sub = cls.objects.get(user=user, status=cls.STATUS_ACTIVE)
        except cls.DoesNotExist:
            return {"status": "error", "error": "No active subscription"}

        try:
            user.update_card_details(payment_method_id)

            price = get_stripe_price(new_plan, new_plan_cycle)
            if not price:
                return {"status": "error", "error": "Invalid plan or cycle"}

            stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
            stripe_sub_data = stripe_sub.get("items", {}).data[0]

            cycle_changed_only = (
                new_plan == user.user_level and sub.cycle != new_plan_cycle
            )
            if not is_upgrade(sub.level, new_plan) or cycle_changed_only:
                return sub.downgrade_or_change_cycle(
                    price,
                    stripe_sub_data.current_period_end,
                    new_plan,
                    new_plan_cycle,
                )

            stripe_sub_to_modify = {"proration_behavior": "always_invoice"}
            if not current_cycle_is_yearly(user) or one_month_left_until_plan_end(user):
                stripe_sub_to_modify["proration_behavior"] = "none"
                stripe_sub_to_modify["billing_cycle_anchor"] = "now"

            stripe_sub = stripe.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=False,
                items=[{"price": price, "id": stripe_sub_data.id}],
                metadata={"plan": new_plan},
                expand=["latest_invoice.payments"],
                **stripe_sub_to_modify,
            )

            stripe_sub_data = stripe_sub.get("items", {}).data[0]
            sub.level = new_plan
            sub.end_date = datetime.fromtimestamp(
                stripe_sub_data.current_period_end,
                tz=now().tzinfo,
            )
            sub.price = Decimal(stripe_sub_data.plan.amount or 0) / 100

            payments = stripe_sub.latest_invoice.payments.data
            payment_intent = (
                stripe.PaymentIntent.retrieve(
                    payments[0].payment.payment_intent,
                )
                if len(payments) > 0
                else None
            )

            if stripe_sub.status == "active":
                sub.status = cls.STATUS_ACTIVE
            elif stripe_sub.status == "incomplete":
                sub.status = cls.STATUS_INCOMPLETE
            elif stripe_sub.status == "past_due":
                sub.status = cls.STATUS_PASTDUE
                sub.is_auto_renew = False

            sub.save()

            if payment_intent and payment_intent.status == "requires_action":
                return {
                    "status": "action_required",
                    "client_secret": payment_intent.client_secret,
                    "subscription": sub,
                }
        except stripe.StripeError as e:
            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success", "subscription": sub}

    def cancel_stripe_subscription(self):
        """Cancel a Stripe subscription"""
        if not self.stripe_subscription_id:
            return {"status": "error", "error": "No Stripe subscription ID"}

        try:
            if self.stripe_subscription_schedule_id:
                stripe.SubscriptionSchedule.release(
                    self.stripe_subscription_schedule_id,
                )

            stripe_sub = stripe.Subscription.modify(
                self.stripe_subscription_id,
                cancel_at_period_end=True,
            )

            self.is_auto_renew = False
            self.save(update_fields=["is_auto_renew"])
        except stripe.StripeError as e:
            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success", "subscription": stripe_sub}

    def cancel_stripe_subscription_immediately(self):
        """Cancel a Stripe subscription immediately"""
        if not self.stripe_subscription_id:
            return {"status": "error", "error": "No Stripe subscription ID"}

        try:
            if self.stripe_subscription_schedule_id:
                stripe.SubscriptionSchedule.release(
                    self.stripe_subscription_schedule_id,
                )

            stripe_sub = stripe.Subscription.delete(self.stripe_subscription_id)
        except stripe.StripeError as e:
            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success", "subscription": stripe_sub}

    def resume_stripe_subscription(self):
        """Resume a Stripe subscription"""
        if not self.stripe_subscription_id:
            return {"status": "error", "error": "No Stripe subscription ID"}

        try:
            if self.stripe_subscription_schedule_id:
                stripe.SubscriptionSchedule.release(
                    self.stripe_subscription_schedule_id,
                )

            stripe_sub = stripe.Subscription.modify(
                self.stripe_subscription_id,
                cancel_at_period_end=False,
            )

            self.is_auto_renew = True
            self.save(update_fields=["is_auto_renew"])
        except stripe.StripeError as e:
            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success", "subscription": stripe_sub}

    def update_from_stripe(self, stripe_sub: stripe.Subscription | None = None):
        """Update subscription details from Stripe"""
        if not self.stripe_subscription_id:
            return {"status": "error", "error": "No Stripe subscription ID"}

        try:
            if not stripe_sub:
                stripe_sub = stripe.Subscription.retrieve(self.stripe_subscription_id)

            # Map Stripe status to our status
            status_map = {
                "active": self.STATUS_ACTIVE,
                "canceled": self.STATUS_CANCELED,
                "incomplete": self.STATUS_INCOMPLETE,
                "incomplete_expired": self.STATUS_EXPIRED,
                "past_due": self.STATUS_PASTDUE,
                "unpaid": self.STATUS_EXPIRED,
                "trialing": self.STATUS_ACTIVE,
            }

            self.status = status_map.get(stripe_sub.status, self.status)
            self.is_auto_renew = stripe_sub.cancel_at_period_end is False

            data = stripe_sub.get("items", {}).get("data", [])[0]
            if current_period_end := data.current_period_end:
                self.end_date = datetime.fromtimestamp(
                    current_period_end,
                    tz=now().tzinfo,
                )

            price = Decimal(data.plan.amount or 0) / 100  # Convert from cents
            self.price = price if price > 0 else self.price
            self.save()
        except stripe.StripeError as e:
            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success", "subscription": stripe_sub}


class Payment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_FAILED, _("Failed")),
        (STATUS_REFUNDED, _("Refunded")),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("user"),
    )
    amount = models.DecimalField(_("amount"), max_digits=6, decimal_places=2)
    payment_date = models.DateTimeField(_("payment date"), default=now)
    status = models.CharField(
        _("status"),
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    description = models.CharField(_("description"), max_length=255)
    transaction_id = models.CharField(
        _("transaction ID"),
        max_length=255,
        blank=True,
        unique=True,
    )
    invoice_url = models.URLField(_("invoice URL"), blank=True)

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.payment_date.strftime('%Y-%m-%d')}"  # noqa: E501

    @property
    def status_badge(self):
        """Return a badge for the payment status"""
        if self.status == self.STATUS_PENDING:
            return "warning"
        if self.status == self.STATUS_COMPLETED:
            return "success"

        return "destructive" if self.status == self.STATUS_FAILED else "secondary"

    def complete(self, transaction_id=None):
        """Mark payment as complete"""
        self.status = self.STATUS_COMPLETED
        if transaction_id:
            self.transaction_id = transaction_id
        self.save()

    def fail(self, description=None):
        """Mark payment as failed"""
        self.status = self.STATUS_FAILED
        if description:
            self.description = description
        self.save(update_fields=["status", "description"])
