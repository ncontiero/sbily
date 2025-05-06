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

LINK_REMOVE_AT_EXCLUDE = r".\d*[-+]\d{2}:\d{2}"

logger = logging.getLogger("links.views")


def home(request: HttpRequest):
    return render(request, "home.html")


def plans(request: HttpRequest):
    return render(request, "plans.html")


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


def create_link(request: HttpRequest):
    if request.method != "POST":
        return redirect("dashboard")

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


def get_current_path(request: HttpRequest):
    current_path = request.POST.get("current_path", reverse("links")).strip()
    if not current_path.startswith("/"):
        current_path = reverse("links")
    return current_path


@login_required
def update_link(request: HttpRequest, shortened_link: str):
    if request.method != "POST":
        return redirect("links")

    current_path = ""

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

        current_path = get_current_path(request)

        form_data = {
            "original_link": request.POST.get("original_link", "").strip(),
            "shortened_link": request.POST.get("shortened_link", "").strip(),
            "remove_at": request.POST.get("remove_at", "").strip(),
            "is_active": request.POST.get("is_active") == "on",
        }

        if not validate([form_data["original_link"]]):
            msg = "Please enter a valid destination URL"
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
            return redirect(current_path)

        in_link_page = current_path.startswith(
            reverse("link", args=[link.shortened_link]),
        )
        if link.shortened_link != form_data["shortened_link"] and in_link_page:
            current_path = reverse("link", args=[form_data["shortened_link"]])

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
def handle_link_activation(request: HttpRequest, shortened_link: str):
    if request.method == "POST":
        return redirect("links")

    current_path = request.GET.get("current_path", reverse("links")).strip()
    if not current_path.startswith("/"):
        current_path = reverse("links")
    try:
        link = ShortenedLink.objects.get(
            shortened_link=shortened_link,
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
        messages.error(request, f"An error occurred: {e}")
        return redirect(current_path)


@login_required
def delete_link(request: HttpRequest, shortened_link: str):
    current_path = reverse("links")

    try:
        current_path = request.GET.get("current_path", reverse("links"))
        if not current_path.startswith("/"):
            current_path = reverse("links")
        link = ShortenedLink.objects.get(
            shortened_link=shortened_link,
            user=request.user,
        )

        if current_path.startswith(reverse("link", args=[link.shortened_link])):
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
