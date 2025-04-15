from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from sbily.payments.admin import LinkPackageInline
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
            _("Permissions"),
            {
                "fields": (
                    "max_num_links",
                    "max_num_links_temporary",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "role",
                    "groups",
                    "user_permissions",
                ),
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
        "permanent_links_used",
        "temporary_links_used",
        "is_active",
    )
    list_filter = ("role", "email_verified", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)


UserAdmin.inlines = [SubscriptionInline, PaymentInline, LinkPackageInline]


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ["user", "type", "created_at", "expires_at"]
    list_filter = ["type", "created_at", "expires_at"]
    search_fields = ["user__username", "type", "token"]
    ordering = ["-created_at"]
    index_together = ["user", "type", "created_at"]
