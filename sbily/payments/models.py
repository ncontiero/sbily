from datetime import datetime
from decimal import Decimal

import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction
from django.utils.timezone import now
from django.utils.timezone import timedelta
from django.utils.translation import gettext_lazy as _

from sbily.users.models import User


class Subscription(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"
    STATUS_INCOMPLETE = "incomplete"
    STATUS_PASTDUE = "past_due"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, _("Active")),
        (STATUS_CANCELED, _("Canceled")),
        (STATUS_EXPIRED, _("Expired")),
        (STATUS_INCOMPLETE, _("Incomplete")),
        (STATUS_PASTDUE, _("Past Due")),
    ]

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
        default=5.00,
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
            self.user.upgrade_to_premium()

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

    @transaction.atomic
    def renew(self, transaction_id: str | None = None):
        """Renew subscription"""
        self.status = self.STATUS_ACTIVE
        self.end_date = now() + timedelta(days=30)
        self.is_auto_renew = True
        self.save()

        Payment.objects.create(
            user=self.user,
            amount=self.price,
            description="Subscription Renewal (30 days)",
            payment_type=Payment.TYPE_SUBSCRIPTION,
            transaction_id=transaction_id,
        )

    @classmethod
    @transaction.atomic
    def create_subscription(cls, user: User, payment_method_id=None):
        """Create a subscription"""

        customer = user.get_stripe_customer()
        try:
            user.update_card_details(payment_method_id)

            sub, _ = cls.objects.get_or_create(
                user=user,
                defaults={
                    "price": Decimal("5.00"),
                    "status": cls.STATUS_INCOMPLETE,
                    "start_date": now(),
                    "end_date": now() + timedelta(days=30),
                    "is_auto_renew": True,
                },
            )

            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {"price": settings.STRIPE_PREMIUM_PRICE_ID},
                ],
                metadata={
                    "user_id": user.id,
                    "subscription_id": sub.id,
                },
                expand=["latest_invoice.payments"],
            )

            sub.stripe_subscription_id = subscription.id
            sub.save(update_fields=["stripe_subscription_id"])

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

    @transaction.atomic
    def update_from_stripe(self, stripe_sub=None):
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

            if stripe_sub.cancel_at_period_end:
                self.is_auto_renew = False
            else:
                self.is_auto_renew = True

            if stripe_sub.current_period_end:
                self.end_date = datetime.fromtimestamp(
                    stripe_sub.current_period_end,
                    tz=now().tzinfo,
                )

            self.save()
        except stripe.error.StripeError as e:
            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success", "subscription": stripe_sub}


class Payment(models.Model):
    TYPE_SUBSCRIPTION = "subscription"
    TYPE_PACKAGE = "package"

    TYPE_CHOICES = [
        (TYPE_SUBSCRIPTION, _("Subscription")),
        (TYPE_PACKAGE, _("Link Package")),
    ]

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
    payment_type = models.CharField(
        _("payment type"),
        max_length=12,
        choices=TYPE_CHOICES,
    )
    description = models.CharField(_("description"), max_length=255)
    transaction_id = models.CharField(_("transaction ID"), max_length=255, blank=True)

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

    def fail(self, error_message=None):
        """Mark payment as failed"""
        self.status = self.STATUS_FAILED
        if error_message:
            self.description += f" - Error: {error_message}"
        self.save()


class LinkPackage(models.Model):
    TYPE_PERMANENT = "permanent"
    TYPE_TEMPORARY = "temporary"

    TYPE_CHOICES = [
        (TYPE_PERMANENT, _("Permanent")),
        (TYPE_TEMPORARY, _("Temporary")),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="link_packages",
        verbose_name=_("user"),
    )
    link_type = models.CharField(
        _("link type"),
        max_length=10,
        choices=TYPE_CHOICES,
    )
    quantity = models.PositiveIntegerField(_("quantity"))
    purchase_date = models.DateTimeField(_("purchase date"), default=now)
    unit_price = models.DecimalField(_("unit price"), max_digits=6, decimal_places=2)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        related_name="packages",
        verbose_name=_("payment"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Link package")
        verbose_name_plural = _("Link packages")

    def __str__(self):
        return f"{self.user.username} - {self.get_link_type_display()} x{self.quantity}"

    @classmethod
    @transaction.atomic
    def buy_link_package(
        cls,
        user: User,
        link_type: str,
        quantity: int,
        payment_method_id=None,
    ):
        """Buy a link package"""
        try:
            unit_price = 1.00 if link_type == "permanent" else 2.00

            cls._validate_package_purchase(user, link_type, quantity, unit_price)

            unit_price = cls._apply_discount(link_type, quantity, unit_price)
            payment, intent = cls._create_payment_and_intent(
                user,
                link_type,
                quantity,
                unit_price,
                payment_method_id,
            )

            if intent.status == "succeeded":
                payment.complete(transaction_id=intent.id)
                cls.objects.create(
                    user=user,
                    link_type=link_type,
                    quantity=quantity,
                    unit_price=unit_price,
                    payment=payment,
                )
                cls._update_user_links(user, link_type, quantity)
                return {"status": "success", "payment": payment, "intent": intent}
            if intent.status in {
                "requires_action",
                "requires_payment_method",
                "requires_confirmation",
            }:
                payment.status = Payment.STATUS_PENDING
                payment.save()
                return {
                    "status": "action_required",
                    "payment": payment,
                    "client_secret": intent.client_secret,
                    "intent": intent,
                }
            payment.status = Payment.STATUS_PENDING
            payment.save()
        except stripe.error.StripeError as e:
            payment.fail(error_message=str(e))
            return {"status": "error", "error": str(e), "payment": payment}
        except (ValueError, ValidationError) as e:
            payment.fail(error_message=str(e))
            return {"status": "error", "error": str(e.message or e)}
        else:
            return {"status": "pending", "payment": payment, "intent": intent}

    @staticmethod
    def _validate_package_purchase(user, link_type, quantity, unit_price):
        if not user.is_premium:
            msg = "User is not premium"
            raise ValidationError(msg)
        if link_type not in dict(LinkPackage.TYPE_CHOICES):
            msg = f"Invalid link type: {link_type}"
            raise ValueError(msg)
        if quantity < 1:
            msg = "Quantity must be greater than 0"
            raise ValueError(msg)
        if unit_price < 0:
            msg = "Unit price must be greater than or equal to 0"
            raise ValueError(msg)

    @staticmethod
    def _apply_discount(link_type, quantity, unit_price):
        discount_with_quantity = 100 if link_type == "permanent" else 50
        if quantity >= discount_with_quantity:
            unit_price *= 0.90  # 10% discount
        return unit_price

    @classmethod
    @transaction.atomic
    def _create_payment_and_intent(
        cls,
        user: User,
        link_type,
        quantity,
        unit_price,
        payment_method_id,
    ):
        customer = user.get_stripe_customer()
        pm = user.update_card_details(payment_method_id)

        payment = Payment.objects.create(
            user=user,
            amount=Decimal(unit_price) * quantity,
            description=f"Purchase of {quantity} {link_type} links",
            payment_type=Payment.TYPE_PACKAGE,
            status=Payment.STATUS_COMPLETED,
        )

        intent = stripe.PaymentIntent.create(
            amount=int(float(payment.amount) * 100),  # Convert to cents
            currency="usd",
            customer=customer.id,
            payment_method_types=["card"],
            description=payment.description,
            metadata={
                "payment_id": payment.id,
                "user_id": user.id,
                "package_type": link_type,
                "quantity": quantity,
            },
            confirm=bool(pm),
            payment_method=pm or None,
        )

        payment.transaction_id = intent.id
        payment.save()
        return payment, intent

    @staticmethod
    def _update_user_links(user, link_type, quantity):
        if link_type == LinkPackage.TYPE_PERMANENT:
            user.max_num_links += quantity
        if link_type == LinkPackage.TYPE_TEMPORARY:
            user.max_num_links_temporary += quantity
        user.save(update_fields=["max_num_links", "max_num_links_temporary"])
