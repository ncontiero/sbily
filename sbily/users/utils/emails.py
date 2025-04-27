from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.timezone import now

from sbily.users.models import User

BASE_URL: str = settings.BASE_URL or ""


def send_email(subject: str, template: str, recipient_list: list[str], **kwargs):
    """Send an email to a list of recipients.

    Args:
        subject: Email subject line.
        template: Path to the email template.
        recipient_list: List of email addresses to send to.
        **kwargs: Additional context data for the email template.
    """

    date_now = now().strftime("%B %d, %Y at %H:%M")
    context = {"BASE_URL": BASE_URL.rstrip("/"), "now": date_now} | kwargs
    message = render_to_string(template, context)

    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=recipient_list,
        fail_silently=False,
        html_message=message,
    )


def send_email_to_user(user: User, subject: str, template: str, **kwargs):
    """Send an email to a user.

    Args:
        user: User object to send email to.
        subject: Email subject line.
        template: Path to the email template.
        **kwargs: Additional context data for the email template.
    """
    if not user.email:
        msg = "User does not have an email address"
        raise ValueError(msg)

    context = {"user": user, "name": user.get_short_name()} | kwargs

    send_email(subject, template, [user.email], **context)
