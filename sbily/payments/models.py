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
from .utils import get_stripe_price


class Subscription(models.Model):
    LEVEL_PREMIUM = PlanType.PREMIUM.value

    STATUS_ACTIVE = "active"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"
    STATUS_INCOMPLETE = "incomplete"
    STATUS_PASTDUE = "past_due"

    LEVEL_CHOICES = [
        (LEVEL_PREMIUM, _("Premium")),
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

            price = get_stripe_price(plan, plan_cycle)
            if not price:
                return {"status": "error", "error": "Invalid plan or cycle"}

            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price}],
                metadata={"user_id": user.id, "plan": plan},
                expand=["latest_invoice.payments"],
            )

            sub.stripe_subscription_id = subscription.id
            sub.level = plan

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
        except stripe.error.StripeError as e:
            if hasattr(sub, "pk") and sub.pk:
                sub.status = cls.STATUS_INCOMPLETE
                sub.save()

            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success", "subscription": sub}

    def cancel_stripe_subscription(self):
        """Cancel a Stripe subscription"""
        if not self.stripe_subscription_id:
            return {"status": "error", "error": "No Stripe subscription ID"}

        try:
            stripe_sub = stripe.Subscription.modify(
                self.stripe_subscription_id,
                cancel_at_period_end=True,
            )

            self.is_auto_renew = False
            self.save(update_fields=["is_auto_renew"])
        except stripe.error.StripeError as e:
            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success", "subscription": stripe_sub}

    def cancel_stripe_subscription_immediately(self):
        """Cancel a Stripe subscription immediately"""
        if not self.stripe_subscription_id:
            return {"status": "error", "error": "No Stripe subscription ID"}

        try:
            stripe_sub = stripe.Subscription.delete(self.stripe_subscription_id)

            self.cancel()
        except stripe.error.StripeError as e:
            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success", "subscription": stripe_sub}

    def resume_stripe_subscription(self):
        """Resume a Stripe subscription"""
        if not self.stripe_subscription_id:
            return {"status": "error", "error": "No Stripe subscription ID"}

        try:
            stripe_sub = stripe.Subscription.modify(
                self.stripe_subscription_id,
                cancel_at_period_end=False,
            )

            self.is_auto_renew = True
            self.save(update_fields=["is_auto_renew"])
        except stripe.error.StripeError as e:
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

            self.save()
        except stripe.error.StripeError as e:
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
