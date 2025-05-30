from django.contrib import admin

from .models import LinkClick
from .models import ShortenedLink


@admin.register(ShortenedLink)
class ShortenedLinkAdmin(admin.ModelAdmin):
    list_display = [
        "destination_url",
        "shortened_path",
        "created_at",
        "updated_at",
        "expires_at",
        "is_active",
    ]
    list_filter = ["created_at", "updated_at", "is_active"]
    search_fields = ["destination_url", "shortened_path", "user__username"]


@admin.register(LinkClick)
class LinkClickAdmin(admin.ModelAdmin):
    list_display = [
        "link",
        "clicked_at",
        "ip_address",
        "country",
        "browser",
        "device_type",
        "operating_system",
    ]
    list_filter = [
        "clicked_at",
        "country",
        "city",
        "browser",
        "device_type",
        "operating_system",
    ]
    search_fields = ["link__destination_url", "ip_address", "referrer"]
