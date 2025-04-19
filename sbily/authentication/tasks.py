from celery import shared_task

from sbily.users.models import User
from sbily.utils.tasks import default_task_params
from sbily.utils.tasks import task_response


@shared_task(**default_task_params("send_sign_in_with_email"))
def send_sign_in_with_email(self, user_id: int):
    """Send sign in with email link to user."""
    user = User.objects.get(id=user_id)

    subject = "Sign in to your account"
    template = "emails/users/sign-in-with-email.html"
    sign_in_with_email_link = user.get_sign_with_email_link()

    user.email_user(
        subject,
        template,
        sign_in_with_email_link=sign_in_with_email_link,
    )
    return task_response(
        "COMPLETED",
        f"Sign in with email sent to {user.username}.",
        user_id=user_id,
    )
