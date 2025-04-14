from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .models import LinkPackage
from .models import Payment
from .models import Subscription
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


class SubscriptionInline(admin.TabularInline):
    model = Subscription
    extra = 0
    readonly_fields = ("start_date",)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("amount", "payment_date", "status", "payment_type", "description")
    readonly_fields = ("payment_date",)


class LinkPackageInline(admin.TabularInline):
    model = LinkPackage
    extra = 0
    fields = ("link_type", "quantity", "purchase_date", "unit_price")
    readonly_fields = ("purchase_date",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "start_date",
        "end_date",
        "is_auto_renew",
        "price",
        "is_active",
    )
    list_filter = ("status", "is_auto_renew")
    search_fields = ("user__username", "user__email")
    date_hierarchy = "start_date"
    actions = ["cancel_subscriptions", "renew_subscriptions"]

    def get_readonly_fields(self, request, obj=None):
        return ("user", "start_date") if obj else ()

    @admin.action(description=_("Cancel selected subscriptions"))
    def cancel_subscriptions(self, request, queryset):
        for subscription in queryset:
            subscription.cancel()
        self.message_user(request, _("Selected subscriptions have been canceled."))

    @admin.action(description=_("Renew selected subscriptions"))
    def renew_subscriptions(self, request, queryset):
        for subscription in queryset:
            subscription.renew()
        self.message_user(request, _("Selected subscriptions have been renewed."))


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "amount",
        "payment_date",
        "status",
        "payment_type",
        "description",
    )
    list_filter = ("status", "payment_type", "payment_date")
    search_fields = ("user__username", "user__email", "description", "transaction_id")
    date_hierarchy = "payment_date"
    actions = ["mark_as_completed", "mark_as_failed", "mark_as_refunded"]

    def get_readonly_fields(self, request, obj=None):
        return ("user", "payment_date") if obj else ()

    @admin.action(description=_("Mark selected payments as completed"))
    def mark_as_completed(self, request, queryset):
        queryset.update(status=Payment.STATUS_COMPLETED)
        self.message_user(
            request,
            _("Selected payments have been marked as completed."),
        )

    @admin.action(description=_("Mark selected payments as failed"))
    def mark_as_failed(self, request, queryset):
        queryset.update(status=Payment.STATUS_FAILED)
        self.message_user(request, _("Selected payments have been marked as failed."))

    @admin.action(description=_("Mark selected payments as refunded"))
    def mark_as_refunded(self, request, queryset):
        queryset.update(status=Payment.STATUS_REFUNDED)
        self.message_user(request, _("Selected payments have been marked as refunded."))


@admin.register(LinkPackage)
class LinkPackageAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "link_type",
        "quantity",
        "purchase_date",
        "unit_price",
        "total_price",
    )
    list_filter = ("link_type", "purchase_date")
    search_fields = ("user__username", "user__email")
    date_hierarchy = "purchase_date"

    def get_readonly_fields(self, request, obj=None):
        return ("user", "purchase_date", "payment") if obj else ()

    @admin.display(
        description=_("Total Price"),
    )
    def total_price(self, obj):
        return obj.quantity * obj.unit_price


UserAdmin.inlines = [SubscriptionInline, PaymentInline, LinkPackageInline]


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ["user", "type", "created_at", "expires_at"]
    list_filter = ["type", "created_at", "expires_at"]
    search_fields = ["user__username", "type", "token"]
    ordering = ["-created_at"]
    index_together = ["user", "type", "created_at"]
