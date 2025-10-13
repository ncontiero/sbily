from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Payment
from .models import Subscription


class SubscriptionInline(admin.TabularInline):
    model = Subscription
    extra = 0
    readonly_fields = ("start_date",)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("amount", "payment_date", "status", "description")
    readonly_fields = ("payment_date",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "level",
        "cycle",
        "status",
        "start_date",
        "end_date",
        "is_auto_renew",
        "price",
        "is_active",
    )
    list_filter = ("level", "status", "is_auto_renew")
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
        "description",
    )
    list_filter = ("status", "payment_date")
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
