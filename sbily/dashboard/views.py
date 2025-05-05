# ruff: noqa: BLE001
import contextlib
import json
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models import Q
from django.db.models.functions import TruncDay
from django.db.models.functions import TruncHour
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone

from sbily.links.models import LinkClick
from sbily.links.models import ShortenedLink

LINK_REMOVE_AT_EXCLUDE = r".\d*[-+]\d{2}:\d{2}"


@login_required
def dashboard(request: HttpRequest):
    links = ShortenedLink.objects.filter(user=request.user)

    clicks = LinkClick.objects.filter(link__user=request.user)
    total_clicks = clicks.count()
    active_links = links.filter(is_active=True).count()
    expired_links = links.filter(remove_at__lt=timezone.now()).count()

    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    clicks_last_30_days = clicks.filter(clicked_at__gte=thirty_days_ago)

    daily_clicks = (
        clicks_last_30_days.annotate(day=TruncDay("clicked_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    # Format dates for JSON serialization
    daily_clicks_data = [
        {"date": item["day"].strftime("%Y-%m-%d"), "count": item["count"]}
        for item in daily_clicks
    ]

    top_links = links.annotate(click_count=Count("clicks")).order_by("-click_count")[:5]
    latest_links = links.order_by("-created_at")[:10]

    # Calculate most active links (most clicks in last 7 days)
    seven_days_ago = timezone.now() - timezone.timedelta(days=7)
    active_links_data = links.annotate(
        recent_clicks=Count("clicks", filter=Q(clicks__clicked_at__gte=seven_days_ago)),
    ).order_by("-recent_clicks")[:5]

    context = {
        "total_clicks": total_clicks,
        "links_count": links.count(),
        "active_links": active_links,
        "expired_links": expired_links,
        "daily_clicks_data": json.dumps(daily_clicks_data),
        "top_links": top_links,
        "latest_links": latest_links,
        "active_links_data": active_links_data,
    }

    if request.user.is_premium:
        country_distribution = (
            clicks_last_30_days.values("country")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        context["country_distribution"] = list(country_distribution)

    return render(request, "dashboard.html", context)


@login_required
def links(request: HttpRequest):
    links = ShortenedLink.objects.filter(user=request.user)
    return render(request, "links.html", {"links": links})


@login_required
def link(request: HttpRequest, shortened_link: str):
    try:
        link = ShortenedLink.objects.get(
            shortened_link=shortened_link,
            user=request.user,
        )

        deactivate = request.GET.get("deactivate")
        if deactivate is not None:
            deactivate = deactivate.lower() == "true"
            link.is_active = not deactivate
            link.save(update_fields=["is_active"])
            messages.success(
                request,
                f"Link {'deactivated' if deactivate else 'activated'}",
            )
            return redirect("links")

        link_remove_at = link.remove_at and re.sub(
            LINK_REMOVE_AT_EXCLUDE,
            "",
            f"{timezone.localtime(link.remove_at)}",
        )
        return render(
            request,
            "link.html",
            {"link": link, "link_remove_at": link_remove_at},
        )
    except ShortenedLink.DoesNotExist:
        messages.error(request, "Link not found")
        return redirect("my_account")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("my_account")


@login_required
def link_statistics(request: HttpRequest, shortened_link: str):
    link = get_object_or_404(
        ShortenedLink,
        shortened_link=shortened_link,
        user=request.user,
    )

    clicks, from_date, to_date = filter_clicks(request, link)
    context = generate_basic_statistics(clicks, link, from_date, to_date)

    if request.user.is_premium:
        context.update(generate_advanced_statistics(request, clicks))

    daily_clicks = (
        clicks.annotate(day=TruncDay("clicked_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    daily_clicks_data = [
        {"date": item["day"].strftime("%Y-%m-%d"), "count": item["count"]}
        for item in daily_clicks
    ]
    context["daily_clicks_data"] = json.dumps(daily_clicks_data)

    return render(request, "statistics/link.html", context)


def filter_clicks(request: HttpRequest, link: ShortenedLink):
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    from_date = request.GET.get("from-date", str(thirty_days_ago.date()))
    to_date = request.GET.get("to-date", None)

    clicks = link.clicks.all()

    if from_date:
        with contextlib.suppress(ValueError):
            from_date = timezone.datetime.strptime(from_date, "%Y-%m-%d")
            from_date = timezone.make_aware(from_date)
            from_date = min(from_date, timezone.localtime())
            clicks = clicks.filter(clicked_at__gte=from_date)
            from_date = from_date.date()

    if to_date:
        with contextlib.suppress(ValueError):
            to_date = timezone.datetime.strptime(to_date, "%Y-%m-%d")
            to_date = timezone.make_aware(to_date) + timezone.timedelta(days=1)
            to_date = min(to_date, timezone.localtime())
            clicks = clicks.filter(clicked_at__lte=to_date)
            to_date = to_date.date()

    return clicks, from_date, to_date


def generate_basic_statistics(clicks, link, from_date, to_date):
    total_clicks = clicks.count()
    clicks_today = clicks.filter(clicked_at__date=timezone.localdate())
    unique_visitors = clicks.values("ip_address").distinct().count()
    unique_visitors_today = clicks_today.values("ip_address").distinct().count()

    return {
        "link": link,
        "total_clicks": total_clicks,
        "clicks_today": clicks_today.count(),
        "unique_visitors": unique_visitors,
        "unique_visitors_today": unique_visitors_today,
        "from_date": from_date,
        "to_date": to_date or timezone.localdate(),
    }


def generate_advanced_statistics(request, clicks):
    device_type = request.GET.get("device_type", None)
    browser = request.GET.get("browser", None)
    operating_system = request.GET.get("operating_system", None)
    country = request.GET.get("country", None)
    city = request.GET.get("city", None)

    filters = {
        "device_type": device_type,
        "browser": browser,
        "operating_system": operating_system,
        "country": country,
        "city": city,
    }

    if device_type:
        clicks = clicks.filter(device_type__icontains=device_type)
    if browser:
        clicks = clicks.filter(browser__icontains=browser)
    if operating_system:
        clicks = clicks.filter(operating_system__icontains=operating_system)
    if country:
        clicks = clicks.filter(country__icontains=country)
    if city:
        clicks = clicks.filter(city__icontains=city)

    hourly_clicks = (
        clicks.annotate(hour=TruncHour("clicked_at"))
        .values("hour")
        .annotate(count=Count("id"))
        .order_by("hour")
    )
    hourly_clicks_data = [
        {"hour": item["hour"].strftime("%H:00"), "count": item["count"]}
        for item in hourly_clicks
    ]

    countries_and_cities = (
        clicks.exclude(country="", city="")
        .values("country", "city")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    devices = (
        clicks.exclude(device_type="")
        .values("device_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    browsers = (
        clicks.exclude(browser="")
        .values("browser")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    operating_systems = (
        clicks.exclude(operating_system="")
        .values("operating_system")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    referrers = (
        clicks.exclude(referrer="")
        .values("referrer")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    return {
        "hourly_clicks_data": json.dumps(hourly_clicks_data),
        "countries_and_cities": list(countries_and_cities),
        "devices": list(devices),
        "browsers": list(browsers),
        "operating_systems": list(operating_systems),
        "referrers": referrers,
        "filters": filters,
    }
