# ruff: noqa: BLE001
from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.shortcuts import render

from .models import Notification

if TYPE_CHECKING:
    from django.http import HttpRequest


@login_required
def my_notifications(request: HttpRequest):
    notifications = Notification.objects.filter(user=request.user)
    return render(request, "my_notifications.html", {"notifications": notifications})


@login_required
def my_notification(request: HttpRequest, notification_id: int):
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.mark_as_read()
        return render(request, "my_notification.html", {"notification": notification})
    except Notification.DoesNotExist:
        messages.error(request, "Notification not found")
        return redirect("my_notifications")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("my_notifications")


@login_required
def handle_read(request: HttpRequest, notification_id: int):
    try:
        notification = Notification.objects.get(id=notification_id)
        is_read = notification.is_read
        if is_read:
            notification.mark_as_unread()
        else:
            notification.mark_as_read()
        messages.success(
            request,
            f"Notification marked as {(is_read and 'unread') or 'read'}",
        )
        return redirect("my_notifications")
    except Notification.DoesNotExist:
        messages.error(request, "Notification not found")
        return redirect("my_notifications")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("my_notifications")


@login_required
def delete_notification(request: HttpRequest, notification_id: int):
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.delete()
        messages.success(request, "Notification deleted")
        return redirect("my_notifications")
    except Notification.DoesNotExist:
        messages.error(request, "Notification not found")
        return redirect("my_notifications")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("my_notifications")


@login_required
def mark_all_as_read(request: HttpRequest):
    try:
        notifications = Notification.objects.filter(user=request.user)
        notifications.update(is_read=True)
        messages.success(request, "All notifications marked as read")
        return redirect("my_notifications")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("my_notifications")


@login_required
def delete_all(request: HttpRequest):
    try:
        notifications = Notification.objects.filter(user=request.user)
        notifications.delete()
        messages.success(request, "All notifications deleted")
        return redirect("my_notifications")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("my_notifications")
