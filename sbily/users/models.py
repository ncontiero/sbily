import contextlib
import json
from decimal import Decimal
from urllib.parse import urljoin

import stripe
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction
from django.urls import reverse
from django.utils.timezone import datetime
from django.utils.timezone import now
from django.utils.timezone import timedelta
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import ClockedSchedule
from django_celery_beat.models import PeriodicTask

from .utils.data import generate_token

BASE_URL = settings.BASE_URL or ""


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_USER = "user"
    ROLE_PREMIUM = "premium"

    MAX_NUM_LINKS_PER_USER = 5
    MAX_NUM_LINKS_PER_PREMIUM_USER = 10
    MAX_NUM_LINKS_TEMP_PER_USER = 2
    MAX_NUM_LINKS_TEMP_PER_PREMIUM_USER = 5

    ROLE_CHOICES = [
        (ROLE_ADMIN, _("Admin")),
        (ROLE_USER, _("User")),
        (ROLE_PREMIUM, _("Premium")),
    ]

    role = models.CharField(
        _("role"),
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_USER,
        help_text=_("User role"),
    )
    email = models.EmailField(_("email address"), unique=True, blank=False, null=False)
    email_verified = models.BooleanField(
        _("email verified"),
        default=False,
        help_text=_("Designates whether the user has verified their email address."),
    )
    login_with_email = models.BooleanField(
        _("login with email"),
        default=False,
        help_text=_("Designates whether the user can login with email."),
    )
    max_num_links = models.PositiveIntegerField(
        _("max number of links"),
        default=MAX_NUM_LINKS_PER_USER,
        help_text=_("Maximum number of links a user can create"),
    )
    max_num_links_temporary = models.PositiveIntegerField(
        _("max number of temporary links"),
        default=MAX_NUM_LINKS_TEMP_PER_USER,
        help_text=_("Maximum number of temporary links a user can create"),
    )
    stripe_customer_id = models.CharField(
        _("Stripe customer ID"),
        max_length=100,
        blank=True,
    )
    card_last_four_digits = models.CharField(
        _("card last four digits"),
        max_length=4,
        blank=True,
    )

    @property
    def is_admin(self) -> bool:
        return self.role == self.ROLE_ADMIN

    @property
    def is_user(self) -> bool:
        return self.role == self.ROLE_USER

    @property
    def is_premium(self) -> bool:
        return self.role == self.ROLE_PREMIUM

    @property
    def permanent_links_used(self):
        """Returns the number of permanent links used"""
        return self.shortened_links.filter(remove_at__isnull=True).count()

    @property
    def temporary_links_used(self):
        """Returns the number of temporary links used"""
        return self.shortened_links.filter(remove_at__isnull=False).count()

    @property
    def permanent_links_left(self):
        """Returns the number of permanent links left for user"""
        return self.max_num_links - self.permanent_links_used

    @property
    def temporary_links_left(self):
        """Returns the number of temporary links left for user"""
        return self.max_num_links_temporary - self.temporary_links_used

    @property
    def permanent_links_used_percentage(self) -> float:
        """Returns the percentage of permanent links used by user"""
        if self.max_num_links == 0:
            return 0
        return min(100, int((self.permanent_links_used / self.max_num_links) * 100))

    @property
    def temporary_links_used_percentage(self) -> float:
        """Returns the percentage of temporary links used by user"""
        if self.max_num_links_temporary == 0:
            return 0
        return min(
            100,
            int((self.temporary_links_used / self.max_num_links_temporary) * 100),
        )

    def save(self, *args, **kwargs):
        if not self.pk:
            role_limits = {
                self.ROLE_ADMIN: (100, 100),
                self.ROLE_PREMIUM: (
                    self.MAX_NUM_LINKS_PER_PREMIUM_USER,
                    self.MAX_NUM_LINKS_TEMP_PER_PREMIUM_USER,
                ),
                self.ROLE_USER: (
                    self.MAX_NUM_LINKS_PER_USER,
                    self.MAX_NUM_LINKS_TEMP_PER_USER,
                ),
            }

            if self.is_superuser:
                self.role = self.ROLE_ADMIN
                self.email_verified = True

            if self.role in role_limits:
                self.max_num_links, self.max_num_links_temporary = role_limits[
                    self.role
                ]

        super().save(*args, **kwargs)

    def can_create_link(self) -> bool:
        """Check if user can create links"""
        return self.permanent_links_left > 0

    def can_create_temporary_link(self) -> bool:
        """Check if user can create temporary links"""
        return self.temporary_links_left > 0

    def upgrade_to_premium(self):
        """Upgrade user to premium"""
        self.role = self.ROLE_PREMIUM
        self.max_num_links = self.MAX_NUM_LINKS_PER_PREMIUM_USER
        self.max_num_links_temporary = self.MAX_NUM_LINKS_TEMP_PER_PREMIUM_USER
        self.save()

    @transaction.atomic
    def downgrade_to_free(self) -> None | str:
        """Downgrade user from premium to free"""
        self.role = self.ROLE_USER

        excess_permalinks = self.permanent_links_used - self.max_num_links
        excess_temporary_links = (
            self.temporary_links_used - self.max_num_links_temporary
        )
        total_deleted = 0

        if excess_permalinks > 0:
            links_to_delete = self.shortened_links.filter(
                remove_at__isnull=True,
            ).order_by("-updated_at")[:excess_permalinks]
            deleted = self.shortened_links.filter(pk__in=links_to_delete).delete()
            total_deleted += deleted[0]

        if excess_temporary_links > 0:
            links_to_delete = self.shortened_links.filter(
                remove_at__isnull=False,
            ).order_by("-updated_at")[:excess_temporary_links]
            deleted = self.shortened_links.filter(pk__in=links_to_delete).delete()
            total_deleted += deleted[0]

        self.max_num_links = self.MAX_NUM_LINKS_PER_USER
        self.max_num_links_temporary = self.MAX_NUM_LINKS_TEMP_PER_USER
        self.save()
        if total_deleted > 0:
            return (
                f"Deleted {total_deleted} excess links due to downgrading to free plan.",
            )
        return None

    def get_subscription_history(self):
        """Get subscription payment history"""
        return self.payments.filter(
            payment_type=Payment.TYPE_SUBSCRIPTION,
        ).order_by("-payment_date")

    def get_package_history(self):
        """Get package purchase history"""
        return self.payments.filter(
            payment_type=Payment.TYPE_PACKAGE,
        ).order_by("-payment_date")

    def get_full_name(self) -> str:
        """Return user's full name or username if not set"""
        return super().get_full_name() or self.username

    def get_short_name(self) -> str:
        """Return user's short name or username if not set"""
        return super().get_short_name() or self.username

    def get_token(
        self,
        token_type: str,
        expires_at: None | datetime = None,
    ) -> str:
        """Gets a token of the given type.

        Args:
            token_type: Type of token to get/create
            expires_at: Optional expiry time for the token

        Returns:
            str: The token string

        Raises:
            ValueError: If token_type is not valid
        """
        if token_type not in dict(Token.TOKEN_TYPE):
            msg = f"Invalid token type: {token_type}"
            raise ValueError(msg)

        token = self.tokens.filter(type=token_type).first() or self.tokens.create(
            type=token_type,
            expires_at=expires_at,
        )

        if token.is_expired():
            token.renew()

        return token.token

    def get_token_link(
        self,
        token_type: str,
        url_name: str,
        expires_at: None | datetime = None,
    ) -> str:
        """Gets a link for a token of the given type.

        Args:
            token_type: Type of token to get/create
            url_name: Name of URL pattern to generate link
            expires_at: Optional expiry time for the token

        Returns:
            str: Full URL containing the token
        """
        token = self.get_token(token_type, expires_at)
        path = reverse(url_name, kwargs={"token": token})
        return urljoin(BASE_URL, path)

    def get_verify_email_link(self) -> str:
        """Generate email verification link for user"""
        if self.email_verified:
            raise ValidationError(_("User email is already verified"), code="verified")

        return self.get_token_link(Token.TYPE_EMAIL_VERIFICATION, "verify_email")

    def get_reset_password_link(self) -> str:
        """Generate password reset link for user"""
        return self.get_token_link(Token.TYPE_PASSWORD_RESET, "reset_password")

    def get_change_email_link(self) -> str:
        """Generate change email link for user"""
        return self.get_token_link(Token.TYPE_CHANGE_EMAIL, "change_email")

    def email_user(
        self,
        subject: str,
        template: str,
        **kwargs,
    ):
        """Send an email to a user with given subject and template.

        Args:
            subject: Email subject
            template: Path to the email template
            **kwargs: Additional context data for the email template
        """
        from .utils.emails import send_email_to_user

        send_email_to_user(
            self,
            subject,
            template,
            **kwargs,
        )

    def get_unread_notifications_count(self) -> int:
        """Get count of unread notifications for user."""
        return self.notifications.filter(is_read=False).count()

    def has_valid_payment_method(self) -> bool:
        """Check if user has a valid payment method in Stripe"""
        if not self.stripe_customer_id:
            return False

        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=self.stripe_customer_id,
                type="card",
            )
            return len(payment_methods.data) > 0
        except stripe.error.StripeError:
            return False

    def get_stripe_customer(self):
        """Get or create Stripe customer for user"""
        if self.stripe_customer_id:
            with contextlib.suppress(stripe.error.StripeError):
                return stripe.Customer.retrieve(self.stripe_customer_id)

        # Create new customer
        customer = stripe.Customer.create(
            email=self.email,
            name=self.get_full_name(),
            metadata={
                "user_id": self.id,
                "username": self.username,
            },
        )

        self.stripe_customer_id = customer.id
        self.save(update_fields=["stripe_customer_id"])

        return customer

    def update_card_details(self, payment_method_id):
        """Update user card details based on payment method"""
        with contextlib.suppress(stripe.error.StripeError):
            pm = stripe.PaymentMethod.retrieve(payment_method_id)
            self.card_last_four_digits = pm.card.last4
            self.save(update_fields=["card_last_four_digits"])

    def create_setup_intent(self):
        """Create a setup intent for adding a payment method"""
        customer = self.get_stripe_customer()

        return stripe.SetupIntent.create(
            customer=customer.id,
            usage="off_session",
        )

    @transaction.atomic
    def process_subscription_payment(self, payment_method_id=None):
        """Process a subscription payment"""
        customer = self.get_stripe_customer()

        payment = Payment.objects.create(
            user=self,
            amount=Decimal("5.00"),
            description="Monthly Premium Subscription",
            payment_type=Payment.TYPE_SUBSCRIPTION,
        )
        try:
            # If payment method provided, attach it to customer
            if payment_method_id:
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=customer.id,
                )
                stripe.Customer.modify(
                    customer.id,
                    invoice_settings={
                        "default_payment_method": payment_method_id,
                    },
                )
                self.update_card_details(payment_method_id)

            # Create the payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(float(payment.amount) * 100),  # Convert to cents
                currency="usd",
                customer=customer.id,
                payment_method_types=["card"],
                description=payment.description,
                metadata={
                    "payment_id": payment.id,
                    "user_id": self.id,
                },
                confirm=not bool(payment_method_id),
            )

            # Update payment with transaction ID
            payment.transaction_id = intent.id

            if intent.status == "succeeded":
                payment.complete(transaction_id=intent.id)
                return {"status": "success", "payment": payment, "intent": intent}
            if intent.status == "requires_action":
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
        else:
            return {"status": "pending", "payment": payment, "intent": intent}

    @transaction.atomic
    def process_package_payment(self, link_type, quantity, payment_method_id=None):
        """Process a payment for a link package"""
        if quantity <= 0:
            return {"status": "failed", "error": "Quantity must be positive"}

        try:
            customer = self.get_stripe_customer()
            discount_with_quantity = 100 if link_type == "permanent" else 50

            unit_price = 1.00 if link_type == "permanent" else 2.00
            total_amount = unit_price * quantity

            if quantity >= discount_with_quantity:
                total_amount *= 0.90  # 10% discount

            # If payment method provided, attach it to customer
            if payment_method_id:
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=customer.id,
                )
                stripe.Customer.modify(
                    customer.id,
                    invoice_settings={
                        "default_payment_method": payment_method_id,
                    },
                )
                self.update_card_details(payment_method_id)

            payment = Payment.objects.create(
                user=self,
                amount=total_amount,
                description=f"Purchase of {quantity} {link_type} links",
                payment_type=Payment.TYPE_PACKAGE,
            )

            # Create the payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(float(payment.amount) * 100),  # Convert to cents
                currency="usd",
                customer=customer.id,
                payment_method_types=["card"],
                description=payment.description,
                metadata={
                    "payment_id": payment.id,
                    "user_id": self.id,
                    "package_type": link_type,
                    "quantity": quantity,
                },
                # confirm=not bool(payment_method_id),
            )
            if not payment_method_id:
                intent = stripe.PaymentIntent.confirm(
                    intent.id,
                    payment_method=customer.invoice_settings.get(
                        "default_payment_method",
                    ),
                )

            # Update payment with transaction ID
            payment.transaction_id = intent.id

            if intent.status == "succeeded":
                payment.complete(transaction_id=intent.id)
                # Create the link package
                # package = LinkPackage.objects.create(
                #     user=self,
                #     link_type=link_type,
                #     quantity=quantity,
                #     unit_price=unit_price,
                #     payment=payment,
                # )

                # Update user's link limits
                # if link_type == LinkPackage.TYPE_PERMANENT:
                #     self.max_num_links += quantity
                # else:
                #     self.max_num_links_temporary += quantity
                # self.save(update_fields=["max_num_links", "max_num_links_temporary"])

                return {
                    "status": "success",
                    "payment": payment,
                    "intent": intent,
                }
            if intent.status == "requires_action":
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
        else:
            return {"status": "pending", "payment": payment, "intent": intent}


class Subscription(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"
    STATUS_INCOMPLETE = "incomplete"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, _("Active")),
        (STATUS_CANCELED, _("Canceled")),
        (STATUS_EXPIRED, _("Expired")),
        (STATUS_INCOMPLETE, _("Incomplete")),
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

    class Meta:
        verbose_name = _("Subscription")
        verbose_name_plural = _("Subscriptions")

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
    def renew(self):
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
        )

    def check_status(self):
        """Check and update subscription status if necessary"""
        if (
            self.status == self.STATUS_ACTIVE
            and self.end_date
            and self.end_date < now()
        ):
            if self.is_auto_renew:
                self.renew()
            else:
                self.status = self.STATUS_EXPIRED
                self.save()

    @transaction.atomic
    def create_stripe_subscription(
        self,
        payment_method_id=None,
    ):
        """Create a Stripe subscription"""

        customer = self.user.get_stripe_customer()

        # If payment method provided, attach it to customer
        default_payment_method = customer.invoice_settings.default_payment_method
        if payment_method_id and payment_method_id != default_payment_method:
            if default_payment_method:
                stripe.PaymentMethod.detach(default_payment_method)
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id,
            )
            stripe.Customer.modify(
                customer.id,
                invoice_settings={
                    "default_payment_method": payment_method_id,
                },
            )
            self.user.update_card_details(payment_method_id)

        try:
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {"price": settings.STRIPE_PREMIUM_PRICE_ID},
                ],
                metadata={
                    "user_id": self.user.id,
                    "subscription_id": self.id,
                },
                expand=["latest_invoice.payments"],
            )

            # Update subscription with Stripe ID
            self.stripe_subscription_id = subscription.id
            payments = subscription.latest_invoice.payments.data
            payment_intent = stripe.PaymentIntent.retrieve(
                payments[0].payment.payment_intent,
            )

            if subscription.status == "active":
                self.status = self.STATUS_ACTIVE
            elif subscription.status == "incomplete":
                self.status = self.STATUS_INCOMPLETE

            self.save()

            if payment_intent and payment_intent.status == "requires_action":
                return {
                    "status": "action_required",
                    "client_secret": payment_intent.client_secret,
                    "subscription": subscription,
                }
        except stripe.error.StripeError as e:
            if hasattr(self, "pk") and self.pk:
                self.status = self.STATUS_INCOMPLETE
                self.save()

            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success", "subscription": subscription}

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
                "past_due": self.STATUS_ACTIVE,  # Handle as still active but might need attention  # noqa: E501
                "unpaid": self.STATUS_EXPIRED,
                "trialing": self.STATUS_ACTIVE,
            }

            self.status = status_map.get(stripe_sub.status, self.status)

            if stripe_sub.cancel_at_period_end:
                self.is_auto_renew = False

            if stripe_sub.current_period_end:
                self.end_date = datetime.fromtimestamp(stripe_sub.current_period_end)

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
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
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
        """Mark payment as complete and apply benefits"""
        self.status = self.STATUS_COMPLETED
        if transaction_id:
            self.transaction_id = transaction_id
        self.save()

        if self.payment_type == self.TYPE_SUBSCRIPTION:
            sub, created = Subscription.objects.get_or_create(
                user=self.user,
                defaults={
                    "status": Subscription.STATUS_ACTIVE,
                    "start_date": now(),
                    "price": self.amount,
                },
            )

            if not created:
                sub.renew()

    def fail(self, error_message=None):
        """Mark payment as failed"""
        self.status = self.STATUS_FAILED
        if error_message:
            self.description += f" - Error: {error_message}"
        self.save()

    def update_status_from_stripe(self):
        """Update payment status from Stripe"""
        if not self.transaction_id:
            return {"status": "error", "error": "No transaction ID"}

        try:
            if self.payment_type == self.TYPE_SUBSCRIPTION:
                try:
                    invoice = stripe.Invoice.retrieve(self.transaction_id)
                    if invoice.status == "paid":
                        self.complete(transaction_id=invoice.payment_intent)
                    elif invoice.status == "uncollectible":
                        self.fail("Payment uncollectible")
                except stripe.error.StripeError:
                    # Not an invoice, try payment intent
                    intent = stripe.PaymentIntent.retrieve(self.transaction_id)
                    if intent.status == "succeeded":
                        self.complete(transaction_id=intent.id)
                    elif intent.status == "canceled":
                        self.fail("Payment canceled")
            else:
                # Regular payment intent
                intent = stripe.PaymentIntent.retrieve(self.transaction_id)
                if intent.status == "succeeded":
                    self.complete(transaction_id=intent.id)
                elif intent.status == "canceled":
                    self.fail("Payment canceled")
        except stripe.error.StripeError as e:
            return {"status": "error", "error": str(e)}
        else:
            return {"status": "success"}


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
        unit_price: float,
        transaction_id: str | None = None,
    ):
        """Buy a link package"""
        if not user.is_premium:
            msg = "User is not premium"
            raise ValidationError(msg)

        if link_type not in dict(cls.TYPE_CHOICES):
            msg = f"Invalid link type: {link_type}"
            raise ValueError(msg)

        if quantity < 1:
            msg = "Quantity must be greater than 0"
            raise ValueError(msg)

        if unit_price < 0:
            msg = "Unit price must be greater than or equal to 0"
            raise ValueError(msg)

        payment = Payment.objects.create(
            user=user,
            amount=Decimal(unit_price) * quantity,
            description=f"Purchase of {quantity} {link_type} links",
            payment_type=Payment.TYPE_PACKAGE,
            transaction_id=transaction_id,
            status=Payment.STATUS_COMPLETED
            if transaction_id
            else Payment.STATUS_PENDING,
        )

        package = cls.objects.create(
            user=user,
            link_type=link_type,
            quantity=quantity,
            unit_price=unit_price,
            payment=payment,
        )

        if link_type == cls.TYPE_PERMANENT:
            user.max_num_links += quantity
        if link_type == cls.TYPE_TEMPORARY:
            user.max_num_links_temporary += quantity

        user.save(update_fields=["max_num_links", "max_num_links_temporary"])

        return payment, package

    @classmethod
    def grant_free_package(cls, user, link_type, quantity, reason):
        """Grant free links to a user (for compensation, promotion, etc.)"""

        payment = Payment.objects.create(
            user=user,
            amount=Decimal("0.00"),
            description=f"Free Link Package ({link_type}) x{quantity} - Reason: {reason}",  # noqa: E501
            payment_type=Payment.TYPE_PACKAGE,
            status=Payment.STATUS_COMPLETED,
        )

        package = cls.objects.create(
            user=user,
            link_type=link_type,
            quantity=quantity,
            unit_price=Decimal("0.00"),
            payment=payment,
        )

        return payment, package


class Token(models.Model):
    DEFAULT_EXPIRY = timedelta(hours=2)
    TYPE_EMAIL_VERIFICATION = "email_verification"
    TYPE_CHANGE_EMAIL = "change_email"
    TYPE_SIGN_IN_WITH_EMAIL = "sign_in_with_email"
    TYPE_PASSWORD_RESET = "password_reset"  # noqa: S105

    TOKEN_TYPE = [
        (TYPE_EMAIL_VERIFICATION, _("Email Verification")),
        (TYPE_CHANGE_EMAIL, _("Change Email")),
        (TYPE_SIGN_IN_WITH_EMAIL, _("Sign In With Email")),
        (TYPE_PASSWORD_RESET, _("Password Reset")),
    ]

    token = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        editable=False,
        help_text=_("Unique token string"),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tokens",
        help_text=_("User this token belongs to"),
    )
    type = models.CharField(
        max_length=20,
        choices=TOKEN_TYPE,
        default=TYPE_EMAIL_VERIFICATION,
        help_text=_("Type of token"),
    )
    expires_at = models.DateTimeField(
        db_index=True,
        editable=False,
        help_text=_("Token expiration date and time"),
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Token")
        verbose_name_plural = _("Tokens")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "type", "created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "type"],
                name="unique_user_token_type",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.type} - {self.token}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = now() + self.DEFAULT_EXPIRY
        if not self.token:
            self.token = generate_token()
        super().full_clean()
        super().save(*args, **kwargs)

        schedule, _ = ClockedSchedule.objects.get_or_create(
            clocked_time=self.expires_at,
        )
        PeriodicTask.objects.update_or_create(
            name=f"Delete token {self.id}",
            defaults={
                "task": "delete_token_by_id",
                "args": json.dumps([self.pk]),
                "clocked": schedule,
                "one_off": True,
                "expires": self.expires_at + timedelta(minutes=1),
                "start_time": self.expires_at,
                "enabled": True,
            },
        )

    def renew(self):
        """Renew token by updating token and timestamps"""
        self.token = generate_token()
        self.expires_at = now() + self.DEFAULT_EXPIRY
        self.save()
        return self.token

    def is_expired(self):
        """Check if token is expired"""
        return self.expires_at and now() > self.expires_at

    def clean(self):
        """Validate token instance"""
        if self.is_expired():
            raise ValidationError(_("This token has expired."), code="expired")
        if self.type == self.TYPE_EMAIL_VERIFICATION and self.user.email_verified:
            raise ValidationError(
                _("This email has already been verified."),
                code="verified",
            )
        if self.type == self.TYPE_CHANGE_EMAIL and not self.user.email_verified:
            raise ValidationError(
                _("This email has not been verified."),
                code="unverified",
            )
        if self.type == self.TYPE_SIGN_IN_WITH_EMAIL and not self.user.email_verified:
            raise ValidationError(
                _("This email has not been verified."),
                code="unverified",
            )
        super().clean()
