# ruff: noqa: BLE001

import logging
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from sbily.utils.data import validate
from sbily.utils.urls import redirect_with_params

from .models import LinkClick
from .models import ShortenedLink

LINK_EXPIRES_AT_EXCLUDE = r".\d*[-+]\d{2}:\d{2}"

logger = logging.getLogger("links.views")


def home(request: HttpRequest):
    return render(request, "home.html")


def plans(request: HttpRequest):
    return render(request, "plans.html")


def redirect_link(request: HttpRequest, shortened_path: str):
    try:
        link = ShortenedLink.objects.get(shortened_path=shortened_path)

        if link.is_expired():
            return render(request, "expired.html")

        if not link.is_active:
            messages.error(request, "Link not found")
            return redirect("home")

        try:
            LinkClick.create_from_request(link, request)
        except Exception as e:
            logger.exception("Error creating link click.", exc_info=e)

        return redirect(link.destination_url)
    except ShortenedLink.DoesNotExist:
        messages.error(request, "Link not found")
        return redirect("home")
    except Exception:
        return redirect("home")


def create_link(request: HttpRequest):
    if request.method != "POST":
        return redirect("dashboard")

    destination_url = request.POST.get("destination_url", "").strip()
    shortened_path = request.POST.get("shortened_path", "").strip()
    expires_at = request.POST.get("expires_at", "").strip()

    try:
        if not validate([destination_url]):
            messages.error(request, "Please enter a valid destination URL")
            return redirect("create_link")

        if not request.user.is_authenticated:
            return redirect_with_params("sign_in", {"destination_url": destination_url})

        link_data = {
            "destination_url": destination_url,
            "shortened_path": shortened_path,
            "user": request.user,
        }

        if expires_at:
            link_data["expires_at"] = timezone.datetime.fromisoformat(
                f"{expires_at}+00:00",
            )

        link = ShortenedLink.objects.create(**link_data)
        messages.success(request, "Link created successfully")
        return redirect("link", shortened_path=link.shortened_path)
    except ValidationError as e:
        messages.error(request, str(e.messages[0]))
        return redirect("create_link")
    except Exception as e:
        messages.error(request, f"An error occurred: {e!s}")
        return redirect("create_link")


def get_current_path(request: HttpRequest):
    current_path = request.POST.get("current_path", reverse("links")).strip()
    if not current_path.startswith("/"):
        current_path = reverse("links")
    return current_path


@login_required
def update_link(request: HttpRequest, shortened_path: str):
    if request.method != "POST":
        return redirect("links")

    current_path = ""

    try:
        link = ShortenedLink.objects.select_for_update().get(
            shortened_path=shortened_path,
            user=request.user,
        )
        link.expires_at = re.sub(
            LINK_EXPIRES_AT_EXCLUDE,
            "",
            f"{timezone.localtime(link.expires_at)}",
        )

        current_path = get_current_path(request)

        form_data = {
            "destination_url": request.POST.get("destination_url", "").strip(),
            "shortened_path": request.POST.get("shortened_path", "").strip(),
            "expires_at": request.POST.get("expires_at", "").strip(),
            "is_active": request.POST.get("is_active") == "on",
        }

        if not validate([form_data["destination_url"]]):
            msg = "Please enter a valid destination URL"
            raise ValidationError(msg)  # noqa: TRY301

        if form_data["expires_at"]:
            form_data["expires_at"] = f"{form_data['expires_at'].replace('T', ' ')}"
        if (
            form_data["destination_url"] == link.destination_url
            and form_data["shortened_path"] == link.shortened_path
            and form_data["expires_at"] == str(link.expires_at)
            and form_data["is_active"] == link.is_active
        ):
            messages.warning(request, "No changes were made")
            return redirect(current_path)

        in_link_page = current_path.startswith(
            reverse("link", args=[link.shortened_path]),
        )
        if link.shortened_path != form_data["shortened_path"] and in_link_page:
            current_path = reverse("link", args=[form_data["shortened_path"]])

        link.destination_url = form_data["destination_url"]
        link.shortened_path = form_data["shortened_path"]
        link.expires_at = None
        if form_data["expires_at"]:
            link.expires_at = timezone.datetime.fromisoformat(
                f"{form_data['expires_at']}+00:00",
            )
        link.is_active = form_data["is_active"]
        link.save()

        messages.success(request, "Link updated successfully")
        return redirect(current_path)
    except ShortenedLink.DoesNotExist:
        messages.error(request, "Link not found")
        return redirect("links")
    except ValidationError as e:
        messages.error(
            request,
            str(e) if isinstance(e.messages, str) else e.messages[0],
        )
        return redirect(current_path)
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("links")


@login_required
def handle_link_activation(request: HttpRequest, shortened_path: str):
    if request.method == "POST":
        return redirect("links")

    current_path = request.GET.get("current_path", reverse("links")).strip()
    if not current_path.startswith("/"):
        current_path = reverse("links")
    try:
        link = ShortenedLink.objects.get(
            shortened_path=shortened_path,
            user=request.user,
        )
        link.is_active = not link.is_active
        link.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "Link updated successfully")
        return redirect(current_path)
    except ShortenedLink.DoesNotExist:
        messages.error(request, "Link not found")
        return redirect("links")
    except Exception as e:
        messages.error(request, f"An error occurred: {e!s}")
        return redirect(current_path)


@login_required
def delete_link(request: HttpRequest, shortened_path: str):
    current_path = reverse("links")

    try:
        current_path = request.GET.get("current_path", reverse("links"))
        if not current_path.startswith("/"):
            current_path = reverse("links")
        link = ShortenedLink.objects.get(
            shortened_path=shortened_path,
            user=request.user,
        )

        if current_path.startswith(reverse("link", args=[link.shortened_path])):
            current_path = reverse("links")

        link.delete()
        messages.success(request, "Link deleted successfully")
        return redirect(current_path)
    except ShortenedLink.DoesNotExist:
        messages.error(request, "Link not found")
        return redirect(current_path)
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect(current_path)


@login_required
def handle_link_actions(request: HttpRequest):
    if request.method != "POST":
        return redirect("links")

    user = request.user
    link_ids = request.POST.getlist("_selected_action")
    action = request.POST.get("action")
    current_path = get_current_path(request)

    shortened_links = ShortenedLink.objects.filter(id__in=link_ids, user=user)

    actions = {
        "delete_selected": shortened_links.delete,
        "activate_selected": shortened_links.update,
        "deactivate_selected": shortened_links.update,
    }

    if not action or action not in actions:
        messages.error(request, "Invalid action")
        return redirect(current_path)
    if not link_ids:
        messages.error(request, "No links selected")
        return redirect(current_path)

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
        return redirect(current_path)
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect(current_path)
    return redirect(current_path)
