from celery import shared_task

from sbily.users.models import Token
from sbily.utils.tasks import default_task_params
from sbily.utils.tasks import task_response


@shared_task(**default_task_params("send_sign_in_with_email"))
def send_sign_in_with_email(self, token_id: int):
    """Send sign in with email link to user."""
    token = Token.objects.get(id=token_id, type=Token.TYPE_SIGN_IN_WITH_EMAIL)
    if not token.is_valid():
        return task_response(
            "FAILED",
            "Token is invalid or expired.",
            token_id=token_id,
        )

    user = token.user
    subject = "Sign in to your account"
    template = "emails/users/sign-in-with-email.html"

    user.email_user(
        subject,
        template,
        sign_in_with_email_link=token.get_link(),
    )
    return task_response(
        "COMPLETED",
        f"Sign in with email sent to {user.username}.",
    )
