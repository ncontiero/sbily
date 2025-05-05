# ruff: noqa: BLE001

import contextlib
import json
import logging
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.db.models import Q
from django.db.models.functions import TruncDay
from django.db.models.functions import TruncHour
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone

from sbily.utils.data import validate
from sbily.utils.urls import redirect_with_params

from .models import LinkClick
from .models import ShortenedLink

LINK_BASE_URL = getattr(settings, "LINK_BASE_URL", None)
LINK_REMOVE_AT_EXCLUDE = r".\d*[-+]\d{2}:\d{2}"

logger = logging.getLogger("links.views")


def home(request: HttpRequest):
    return render(request, "home.html", {"LINK_BASE_URL": LINK_BASE_URL})


def plans(request: HttpRequest):
    return render(request, "plans.html")


def create_link(request: HttpRequest):
    if request.method != "POST":
        return render(request, "create_link.html", {"LINK_BASE_URL": LINK_BASE_URL})

    original_link = request.POST.get("original_link", "").strip()
    shortened_link = request.POST.get("shortened_link", "").strip()
    remove_at = request.POST.get("remove_at", "").strip()
    is_temporary = request.POST.get("is_temporary") == "on"

    try:
        if not validate([original_link]):
            messages.error(request, "Please enter a valid original link")
            return redirect("create_link")

        if not request.user.is_authenticated:
            return redirect_with_params("sign_in", {"original_link": original_link})

        link_data = {
            "original_link": original_link,
            "shortened_link": shortened_link,
            "user": request.user,
        }

        if is_temporary:
            link_data["remove_at"] = timezone.now() + ShortenedLink.DEFAULT_EXPIRY
        if remove_at:
            link_data["remove_at"] = timezone.datetime.fromisoformat(
                f"{remove_at}+00:00",
            )

        link = ShortenedLink.objects.create(**link_data)
        messages.success(request, "Link created successfully")
        return redirect("link", shortened_link=link.shortened_link)
    except ValidationError as e:
        messages.error(request, str(e.messages[0]))
        return redirect("create_link")
    except Exception as e:
        messages.error(request, f"An error occurred: {e!s}")
        return redirect("create_link")


def redirect_link(request: HttpRequest, shortened_link: str):
    try:
        link = ShortenedLink.objects.get(shortened_link=shortened_link)
        if not link.is_functional():
            messages.error(request, "Link is expired or deactivated")
            if request.user == link.user:
                return redirect("link", link.shortened_link)
            return redirect("home")

        try:
            LinkClick.create_from_request(link, request)
        except Exception as e:
            logger.exception("Error creating link click.", exc_info=e)

        return redirect(link.original_link)
    except ShortenedLink.DoesNotExist:
        messages.error(request, "Link not found")
        return redirect("home")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("home")


@login_required
def links(request: HttpRequest):
    user = request.user
    links = ShortenedLink.objects.filter(user=user)

    return render(request, "links.html", {"links": links})


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
            {
                "link": link,
                "link_remove_at": link_remove_at,
                "LINK_BASE_URL": LINK_BASE_URL,
            },
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


@login_required
def update_link(request: HttpRequest, shortened_link: str):
    if request.method != "POST":
        return redirect("links")

    old_shortened_link = shortened_link

    try:
        link = ShortenedLink.objects.select_for_update().get(
            shortened_link=shortened_link,
            user=request.user,
        )
        link.remove_at = re.sub(
            LINK_REMOVE_AT_EXCLUDE,
            "",
            f"{timezone.localtime(link.remove_at)}",
        )

        form_data = {
            "original_link": request.POST.get("original_link", "").strip(),
            "shortened_link": request.POST.get("shortened_link", "").strip(),
            "remove_at": request.POST.get("remove_at", "").strip(),
            "is_active": request.POST.get("is_active") == "on",
        }

        if not validate([form_data["original_link"]]):
            msg = "Please enter a valid original link"
            raise ValidationError(msg)  # noqa: TRY301

        if form_data["remove_at"]:
            form_data["remove_at"] = f"{form_data['remove_at'].replace('T', ' ')}"
        if (
            form_data["original_link"] == link.original_link
            and form_data["shortened_link"] == link.shortened_link
            and form_data["remove_at"] == str(link.remove_at)
            and form_data["is_active"] == link.is_active
        ):
            messages.warning(request, "No changes were made")
            return redirect("link", old_shortened_link)

        link.original_link = form_data["original_link"]
        link.shortened_link = form_data["shortened_link"]
        link.remove_at = None
        if form_data["remove_at"]:
            link.remove_at = timezone.datetime.fromisoformat(
                f"{form_data['remove_at']}+00:00",
            )
        link.is_active = form_data["is_active"]
        link.save()

        messages.success(request, "Link updated successfully")
        return redirect("link", link.shortened_link)
    except ShortenedLink.DoesNotExist:
        messages.error(request, "Link not found")
        return redirect("links")
    except ValidationError as e:
        messages.error(
            request,
            str(e) if isinstance(e.messages, str) else e.messages[0],
        )
        return redirect("link", old_shortened_link)
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("links")


@login_required
def delete_link(request: HttpRequest, shortened_link: str):
    try:
        link = ShortenedLink.objects.get(
            shortened_link=shortened_link,
            user=request.user,
        )

        link.delete()
        messages.success(request, "Link deleted successfully")
        return redirect("links")
    except ShortenedLink.DoesNotExist:
        messages.error(request, "Link not found")
        return redirect("links")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("links")


@login_required
def handle_link_actions(request: HttpRequest):
    if request.method != "POST":
        return redirect("links")

    user = request.user
    link_ids = request.POST.getlist("_selected_action")
    action = request.POST.get("action")

    shortened_links = ShortenedLink.objects.filter(id__in=link_ids, user=user)

    actions = {
        "delete_selected": shortened_links.delete,
        "activate_selected": shortened_links.update,
        "deactivate_selected": shortened_links.update,
    }

    if not action or action not in actions:
        messages.error(request, "Invalid action")
        return redirect("links")
    if not link_ids:
        messages.error(request, "No links selected")
        return redirect("links")

    try:
        if action in ("activate_selected", "deactivate_selected"):
            actions[action](is_active=action == "activate_selected")
        else:
            actions[action]()
        messages.success(request, f"Links {action.split('_')[0]}d successfully")
    except ValidationError as e:
        messages.error(
            request,
            str(e) if isinstance(e.messages, str) else e.messages[0],
        )
        return redirect("links")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("links")
    return redirect("links")
