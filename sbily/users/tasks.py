from celery import shared_task
from celery.utils.log import get_task_logger

from sbily.utils.tasks import default_task_params
from sbily.utils.tasks import task_response

from .models import Token
from .models import User
from .utils.emails import send_email

logger = get_task_logger(__name__)


@shared_task(**default_task_params("send_welcome_email"))
def send_welcome_email(self, user_id: int):
    """
    Send a welcome email to a newly registered user.

    Also schedules a verification email to be sent after a 5-second delay.
    """
    user = User.objects.get(id=user_id)
    name = user.get_short_name()

    subject = f"Welcome to Sbily, {name}!"
    template = "emails/users/welcome.html"

    user.email_user(subject, template)
    try:
        token, _ = Token.get_or_create_for_user(user, Token.TYPE_EMAIL_VERIFICATION)
        send_email_verification.apply_async([token.id], countdown=5)
    except Exception:
        logger.exception("Failed to send verification email to %s", user.username)

    return task_response(
        "COMPLETED",
        f"Welcome email sent to {user.username}.",
        user_id=user_id,
    )


@shared_task(**default_task_params("send_email_verification"))
def send_email_verification(self, token_id: int):
    """Send email verification link to user."""
    token = Token.objects.get(id=token_id, type=Token.TYPE_EMAIL_VERIFICATION)
    if not token.is_valid():
        return task_response(
            "FAILED",
            "Token is invalid or expired.",
            token_id=token_id,
        )

    user = token.user
    subject = "Verify your email address"
    template = "emails/users/verify-email.html"

    user.email_user(
        subject,
        template,
        verify_email_link=token.get_link(),
    )
    return task_response(
        "COMPLETED",
        f"Verification email sent to {user.username}.",
    )


@shared_task(**default_task_params("send_password_reset_email"))
def send_password_reset_email(self, token_id: int):
    """Send password reset link to user."""
    token = Token.objects.get(id=token_id, type=Token.TYPE_PASSWORD_RESET)
    if not token.is_valid():
        return task_response(
            "FAILED",
            "Token is invalid or expired.",
            token_id=token_id,
        )

    user = token.user

    subject = "Reset your password"
    template = "emails/users/reset-password.html"

    user.email_user(
        subject,
        template,
        reset_password_link=token.get_link(),
    )
    return task_response(
        "COMPLETED",
        f"Password reset email sent to {user.username}.",
    )


@shared_task(**default_task_params("send_password_changed_email"))
def send_password_changed_email(self, user_id: int):
    """Send email informing user that their password has been changed."""
    user = User.objects.get(id=user_id)

    subject = "Your password has been changed!"
    template = "emails/users/password-changed.html"

    user.email_user(subject, template)
    return task_response(
        "COMPLETED",
        f"Password changed email sent to {user.username}.",
        user_id=user_id,
    )


@shared_task(**default_task_params("send_email_change_instructions"))
def send_email_change_instructions(self, token_id: int):
    """Send email change instructions to user."""
    token = Token.objects.get(id=token_id, type=Token.TYPE_CHANGE_EMAIL)
    if not token.is_valid():
        return task_response(
            "FAILED",
            "Token is invalid or expired.",
            token_id=token_id,
        )

    subject = "Change your email address"
    template = "emails/users/change-email.html"

    token.user.email_user(
        subject,
        template,
        change_email_link=token.get_link(),
    )
    return task_response(
        "COMPLETED",
        f"Email change instructions sent to {token.user.username}.",
    )


@shared_task(**default_task_params("send_email_changed_email"))
def send_email_changed_email(self, token_id: int, old_email: str):
    """Send email informing user that their email has been changed."""
    token = Token.objects.get(id=token_id, type=Token.TYPE_EMAIL_VERIFICATION)
    if not token.is_valid():
        return task_response(
            "FAILED",
            "Token is invalid or expired.",
            token_id=token_id,
        )

    user = token.user

    subject = "Your email has been changed!"
    template = "emails/users/email-changed.html"
    context = {
        "old_email": old_email,
        "verify_email_link": token.get_link(),
    }
    old_email_context = {
        "user": user,
        "name": user.get_short_name(),
        "is_old": True,
    } | context

    user.email_user(subject, template, **context)
    send_email(subject, template, [old_email], **old_email_context)

    return task_response(
        "COMPLETED",
        f"Email changed email sent to {user.username}.",
    )


@shared_task(**default_task_params("send_deleted_account_email"))
def send_deleted_account_email(self, user_email: int, username: str):
    """Send email informing user that their account has been deleted."""
    subject = "Your account has been deleted"
    template = "emails/users/account-deleted.html"

    send_email(subject, template, [user_email], username=username, name=username)
    return task_response(
        "COMPLETED",
        f"Account deleted email sent to {user_email}.",
        user_email=user_email,
    )
