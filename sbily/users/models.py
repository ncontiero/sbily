import contextlib
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
    def premium_expiry(self) -> datetime | None:
        """Returns the premium expires at date"""
        return self.subscription.end_date or None

    @property
    def is_premium(self) -> bool:
        return self.role == self.ROLE_PREMIUM and self.subscription.is_active

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

        return (
            f"Deleted {total_deleted} excess links due to downgrading to free plan."
            if total_deleted > 0
            else None
        )

    def get_full_name(self) -> str:
        """Return user's full name or username if not set"""
        return super().get_full_name() or self.username

    def get_short_name(self) -> str:
        """Return user's short name or username if not set"""
        return super().get_short_name() or self.username

    def create_token(
        self,
        token_type: str,
        expires_in: timedelta | None = None,
        **kwargs,
    ) -> "Token":
        """Creates a new token of the given type.

        Args:
            token_type: Type of token to create
            expires_in: Optional timedelta for token expiration (from now)
            **kwargs: Additional fields to set on the token

        Returns:
            Token: The newly created token

        Raises:
            ValueError: If token_type is not valid
        """

        return Token.create_for_user(
            user=self,
            token_type=token_type,
            expires_in=expires_in,
            **kwargs,
        )

    def get_token(
        self,
        token_type: str,
        expires_in: datetime | None = None,
        **kwargs,
    ) -> str:
        """Gets a token of the given type, creating if needed.

        Args:
            token_type: Type of token to get/create
            expires_in: Optional timedelta for token expiration (from now)
            **kwargs: Additional fields to set on the token if created

        Returns:
            str: The token string

        Raises:
            ValueError: If token_type is not valid
        """
        if token_type not in dict(Token.TOKEN_TYPE):
            msg = f"Invalid token type: {token_type}"
            raise ValueError(msg)

        with contextlib.suppress(Token.DoesNotExist):
            token = self.tokens.get(type=token_type, is_used=False)
            if not token.is_expired():
                return token.token

        return self.create_token(token_type, expires_in, **kwargs).token

    def get_token_link(
        self,
        token_type: str,
        url_name: str,
        expires_in: timedelta | None = None,
        **kwargs,
    ) -> str:
        """Gets a link for a token of the given type.

        Args:
            token_type: Type of token to get/create
            url_name: Name of URL pattern to generate link
            expires_in: Optional timedelta for token expiration (from now)
            **kwargs: Additional fields to set on the token if created

        Returns:
            str: Full URL containing the token
        """
        token_string = self.get_token(token_type, expires_in, **kwargs)
        path = reverse(url_name, kwargs={"token": token_string})
        return urljoin(BASE_URL, path)

    def get_verify_email_link(self, **kwargs) -> str:
        """Generate email verification link for user"""
        if self.email_verified:
            raise ValidationError(_("User email is already verified"), code="verified")

        return self.get_token_link(
            Token.TYPE_EMAIL_VERIFICATION,
            "verify_email",
            **kwargs,
        )

    def get_reset_password_link(self, **kwargs) -> str:
        """Generate password reset link for user"""
        return self.get_token_link(
            Token.TYPE_PASSWORD_RESET,
            "reset_password",
            **kwargs,
        )

    def get_change_email_link(self, **kwargs) -> str:
        """Generate change email link for user"""
        if not self.email_verified:
            raise ValidationError(_("Current email is not verified"), code="unverified")

        return self.get_token_link(
            Token.TYPE_CHANGE_EMAIL,
            "change_email",
            **kwargs,
        )

    def get_sign_with_email_link(self, **kwargs) -> str:
        """Generate sign with email link for user"""
        if not self.email_verified:
            raise ValidationError(_("Email is not verified"), code="unverified")
        if not self.login_with_email:
            raise ValidationError(
                _("User does not have permission to login with email"),
                code="permission_denied",
            )

        expires_in = timedelta(minutes=15)
        return self.get_token_link(
            Token.TYPE_SIGN_IN_WITH_EMAIL,
            "sign_in_with_email_verify",
            expires_in=expires_in,
            **kwargs,
        )

    @classmethod
    def validate_token(
        cls,
        token_string: str,
        token_type: str,
    ) -> tuple[bool, "User", str]:
        """
        Validates a token and returns the associated user if valid.

        Args:
            token_string: A string do token a ser validada
            token_type: O tipo esperado do token

        Returns:
            tuple: (is_valid, user or None, error message or '')
        """
        try:
            token = Token.get_valid_token(token_string, token_type)

            if not token:
                return False, None, _("Token is invalid or expired")
            if token.type != token_type:
                return False, None, _("Invalid token type")

            if (
                token_type == Token.TYPE_EMAIL_VERIFICATION
                and token.user.email_verified
            ):
                return False, token.user, _("Email is already verified")

            if (
                token_type in (Token.TYPE_CHANGE_EMAIL, Token.TYPE_SIGN_IN_WITH_EMAIL)
                and not token.user.email_verified
            ):
                return False, token.user, _("Email is not verified")
        except Exception as e:  # noqa: BLE001
            return False, None, str(e)
        else:
            return True, token.user, ""

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

            customer = self.get_stripe_customer()
            default_payment_method = customer.invoice_settings.get(
                "default_payment_method",
            )
            if pm.id != default_payment_method:
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

            self.card_last_four_digits = pm.card.last4
            self.save(update_fields=["card_last_four_digits"])

            return pm.id


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
        help_text=_("Token expiration date and time"),
    )
    is_used = models.BooleanField(
        default=False,
        help_text=_("Whether this token has been used"),
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Token")
        verbose_name_plural = _("Tokens")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "type", "created_at"]),
            models.Index(fields=["token"]),
            models.Index(fields=["expires_at", "is_used"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "type"],
                condition=models.Q(is_used=False),
                name="unique_active_user_token_type",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_type_display()} - {self.token[:8]}..."

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = now() + self.DEFAULT_EXPIRY
        if not self.token:
            self.token = self.generate_token()
        super().save(*args, **kwargs)

    @classmethod
    def generate_token(cls, length: int = 32):
        """Generate a unique token string"""
        token = generate_token(length)
        while cls.objects.filter(token=token).exists():
            token = generate_token(length)
        return token

    def mark_as_used(self):
        """Mark token as used"""
        self.is_used = True
        self.save(update_fields=["is_used", "updated_at"], force_update=True)

    def is_expired(self):
        """Check if token is expired"""
        return bool(self.expires_at and now() > self.expires_at)

    def is_valid(self):
        """Check if token is valid (not expired and not used)"""
        return not self.is_expired() and not self.is_used

    def clean(self):
        """Validate token instance"""
        if self.is_expired():
            raise ValidationError(_("This token has expired."), code="expired")

        if self.is_used:
            raise ValidationError(_("This token has already been used."), code="used")

        if self.type == self.TYPE_EMAIL_VERIFICATION and self.user.email_verified:
            raise ValidationError(
                _("This email has already been verified."),
                code="verified",
            )

        if self.type == self.TYPE_CHANGE_EMAIL and not self.user.email_verified:
            raise ValidationError(
                _("Current email has not been verified."),
                code="unverified",
            )

        if self.type == self.TYPE_SIGN_IN_WITH_EMAIL and not self.user.email_verified:
            raise ValidationError(
                _("This email has not been verified."),
                code="unverified",
            )

        super().clean()

    @classmethod
    def create_for_user(
        cls,
        user: User,
        token_type: str,
        expires_in: None | timedelta = None,
        **extra_fields,
    ):
        """
        Creates a new token for the specified user and type.
        Overwrites any existing token of the same type for the user

        Args:
            user: User to create token for
            token_type: Type of token to create
            expires_in: Optional expiry time for the token
            **extra_fields: Additional fields to set on the token
        Returns:
            Token: The created token instance
        Raises:
            ValueError: If token_type is not valid
        """

        if token_type not in dict(cls.TOKEN_TYPE):
            msg = f"Invalid token type: {token_type}"
            raise ValueError(msg)

        cls.objects.filter(user=user, type=token_type, is_used=False).update(
            is_used=True,
        )

        expires_at = now() + (expires_in or cls.DEFAULT_EXPIRY)
        return cls.objects.create(
            user=user,
            type=token_type,
            expires_at=expires_at,
            **extra_fields,
        )

    @classmethod
    def get_valid_token(
        cls,
        token_string: str,
        token_type: str | None = None,
    ) -> "None | Token":
        """Returns a valid token by the value string or None"""
        query = cls.objects.filter(token=token_string, is_used=False)

        if token_type is not None:
            query = query.filter(type=token_type)

        with contextlib.suppress(cls.DoesNotExist):
            token = query.get()
            if token.is_valid():
                return token

        return None
