from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import admin as auth_admin
from django.db.models import F
from django.db.models.functions import Greatest
from django.db.models.functions import Now
from django.utils.timezone import timedelta
from django.utils.translation import gettext_lazy as _

from sbily.payments.admin import PaymentInline
from sbily.payments.admin import SubscriptionInline

from .models import Token
from .models import User


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "email_verified",
                    "login_with_email",
                ),
            },
        ),
        (
            _("Role & Limits"),
            {"fields": ("role", "monthly_link_limit", "monthly_limit_links_used")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("collapse",),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
        (
            _("Payment info"),
            {
                "fields": (
                    "stripe_customer_id",
                    "card_last_four_digits",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    list_display = (
        "username",
        "email",
        "role",
        "email_verified",
        "monthly_limit_links_used",
        "is_active",
    )
    list_filter = (
        "role",
        "email_verified",
        "is_active",
        "is_staff",
        "date_joined",
    )
    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "stripe_customer_id",
    )
    ordering = ("-date_joined",)
    inlines = [SubscriptionInline, PaymentInline]


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "type",
        "is_valid_token",
        "created_at",
        "expires_at",
        "is_used",
    ]
    list_filter = ["type", "is_used", "expires_at", "created_at"]
    search_fields = ["user__username", "user__email", "token"]
    raw_id_fields = ["user"]
    readonly_fields = ["token", "created_at", "updated_at", "token_preview"]
    date_hierarchy = "created_at"
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "user",
                    "type",
                    "token_preview",
                    "expires_at",
                    "is_used",
                ],
            },
        ),
        (
            _("Additional Information"),
            {
                "fields": [
                    "created_at",
                    "updated_at",
                ],
                "classes": ["collapse"],
            },
        ),
    ]
    actions = ["renew_tokens", "mark_as_used", "extend_expiry_24h"]

    @admin.display(description=_("Token Preview"), ordering="token")
    def token_preview(self, obj):
        return f"{obj.token[:10]}...{obj.token[-4:]}" if obj.token else "—"

    @admin.display(boolean=True, description=_("Is Valid"))
    def is_valid_token(self, obj):
        return obj.is_valid()

    @admin.action(description=_("Renew selected tokens"))
    def renew_tokens(self, request, queryset):
        updated = queryset.update(
            token=Token.generate_token(),
            is_used=False,
            expires_at=Greatest(F("expires_at"), Now()) + timedelta(hours=2),
            updated_at=Now(),
        )
        self.message_user(
            request,
            _("Successfully renewed %(count)d tokens.") % {"count": updated},
            messages.SUCCESS,
        )

    @admin.action(description=_("Mark selected tokens as used"))
    def mark_as_used(self, request, queryset):
        count = queryset.update(is_used=True)
        self.message_user(
            request,
            _("Successfully marked %(count)d tokens as used.") % {"count": count},
            messages.SUCCESS,
        )

    @admin.action(description=_("Extend expiry by 24 hours"))
    def extend_expiry_24h(self, request, queryset):
        extended = queryset.update(
            expires_at=Greatest(F("expires_at"), Now()) + timedelta(hours=24),
            updated_at=Now(),
        )
        self.message_user(
            request,
            _("Successfully extended expiry for %(count)d tokens by 24 hours.")
            % {"count": extended},
            messages.SUCCESS,
        )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("user")
