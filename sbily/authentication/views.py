# ruff: noqa: BLE001
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import logout
from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.timezone import now
from django.utils.timezone import timedelta

from sbily.links.models import ShortenedLink
from sbily.users.models import Token
from sbily.users.tasks import send_password_changed_email
from sbily.users.tasks import send_password_reset_email
from sbily.users.tasks import send_welcome_email
from sbily.utils.errors import BadRequestError
from sbily.utils.errors import bad_request_error
from sbily.utils.urls import reverse_with_params

from .forms import ForgotPasswordForm
from .forms import ResetPasswordForm
from .forms import SignInForm
from .forms import SignInWithEmailForm
from .forms import SignUpForm
from .tasks import send_sign_in_with_email


def get_post_auth_redirect(request, user, form):
    """
    Determine the redirect path after authentication.
    """
    plan = form.cleaned_data.get("plan", "free")
    cycle = form.cleaned_data.get("cycle", "monthly")
    destination_url = form.cleaned_data.get("destination_url", "")
    next_path = form.cleaned_data.get("next_path", "my_account")

    if plan == "premium":
        return redirect(reverse_with_params("upgrade_plan", {"cycle": cycle}))

    if destination_url:
        link = ShortenedLink.objects.create(
            destination_url=destination_url,
            user=user,
        )
        messages.success(request, "Link created successfully.")
        return redirect("link", shortened_path=link.shortened_path)

    return redirect(next_path)


def sign_up(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("my_account")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                send_welcome_email.delay_on_commit(user.id)
                messages.success(
                    request,
                    "User created successfully! Please verify your email.",
                )

                return get_post_auth_redirect(request, user, form)
            except Exception as e:
                messages.error(request, f"Error signing up: {e}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm(
            initial={
                "plan": request.GET.get("plan"),
                "cycle": request.GET.get("cycle"),
                "next_path": request.GET.get("next"),
                "destination_url": request.GET.get("destination_url"),
            },
        )

    sign_in_url = reverse_with_params(
        "sign_in",
        {
            "next": request.GET.get("next"),
            "destination_url": request.GET.get("destination_url"),
        },
    )

    return render(request, "sign_up.html", {"form": form, "sign_in_url": sign_in_url})


def sign_in(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("my_account")

    if request.method == "POST":
        form = SignInForm(request.POST)
        if form.is_valid():
            try:
                user = form.cleaned_data["user"]
                login(request, user)

                return get_post_auth_redirect(request, user, form)
            except Exception as e:
                messages.error(request, f"Error signing in: {e}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignInForm(
            initial={
                "next_path": request.GET.get("next", "my_account"),
                "destination_url": request.GET.get("destination_url"),
            },
        )

    sign_up_url = reverse_with_params(
        "sign_up",
        {
            "next": request.GET.get("next", "my_account"),
            "destination_url": request.GET.get("destination_url"),
        },
    )

    return render(request, "sign_in.html", {"form": form, "sign_up_url": sign_up_url})


def sign_in_with_email(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("my_account")
    if request.method != "POST":
        form = SignInWithEmailForm()
        return render(request, "sign_in_with_email.html", {"form": form})

    form = SignInWithEmailForm(request.POST)

    if form.is_valid():
        try:
            user = form.cleaned_data.get("user")

            token, created = Token.get_or_create_for_user(
                user,
                Token.TYPE_SIGN_IN_WITH_EMAIL,
            )
            if not created and token.updated_at > now() - timedelta(minutes=15):
                bad_request_error(
                    "You can only request sign in link once every 15 minutes",
                )

            send_sign_in_with_email.delay_on_commit(token.id)
            messages.success(
                request,
                "Please check your email for a sign in link.",
            )
            return redirect("sign_in")
        except Exception as e:
            messages.error(request, f"Error sending sign in link: {e!s}")
            return redirect("sign_in_with_email")

    return render(request, "sign_in_with_email.html", {"form": form})


def sign_in_with_email_verify(request: HttpRequest, token: str):
    token_obj = Token.get_valid_token(token, Token.TYPE_SIGN_IN_WITH_EMAIL)

    if request.user.is_authenticated:
        if token_obj and token_obj.user == request.user:
            token_obj.mark_as_used()
        return redirect("my_account")

    try:
        if not token_obj:
            bad_request_error(
                "Token has expired or is invalid! Please request a new one",
            )
        if not token_obj.user.login_with_email:
            bad_request_error("Please enable login with email")

        token_obj.mark_as_used()
        login(request, token_obj.user)
        messages.success(request, "Signed in successfully")
        return redirect("my_account")
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect("sign_in_with_email")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("sign_in_with_email")


def sign_out(request):
    logout(request)
    return redirect("sign_in")


def verify_email(request: HttpRequest, token: str):
    user = request.user
    is_authenticated = user.is_authenticated
    redirect_url_name = (
        reverse_with_params("my_account", {"tab": "email"})
        if is_authenticated
        else "sign_in"
    )

    try:
        obj_token = Token.get_valid_token(token, Token.TYPE_EMAIL_VERIFICATION)

        if obj_token is None or (is_authenticated and user != obj_token.user):
            bad_request_error(
                "Token has expired or is invalid! Please request a new one",
            )
        if obj_token.user.email_verified:
            bad_request_error("Email has already been verified")

        with transaction.atomic():
            user.email_verified = True
            user.save(update_fields=["email_verified"])
            obj_token.mark_as_used()
        messages.success(request, "Email verified successfully")
        return redirect(redirect_url_name)
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect(redirect_url_name)
    except Exception as e:
        messages.error(request, f"Error verifying email: {e}")
        return redirect(redirect_url_name)


def forgot_password(request: HttpRequest):
    if request.method != "POST":
        email = request.GET.get("email", "")
        form = ForgotPasswordForm(initial={"email": email})
        return render(request, "forgot_password.html", {"form": form})

    form = ForgotPasswordForm(request.POST)

    if form.is_valid():
        try:
            user = form.cleaned_data.get("user")

            token, created = Token.get_or_create_for_user(
                user,
                Token.TYPE_PASSWORD_RESET,
            )
            if not created and token.updated_at > now() - timedelta(minutes=15):
                bad_request_error(
                    "You can only request password reset once every 15 minutes",
                )

            send_password_reset_email.delay_on_commit(token.id)
            messages.success(request, "Password reset email sent successfully")
            return redirect("sign_in")
        except BadRequestError as e:
            messages.error(request, e.message)
            return redirect("forgot_password")
        except Exception as e:
            messages.error(request, f"Error sending password reset email: {e!s}")
            return redirect("forgot_password")

    return render(request, "forgot_password.html", {"form": form})


def reset_password(request: HttpRequest, token: str):
    obj_token = Token.get_valid_token(token, Token.TYPE_PASSWORD_RESET)

    if obj_token is None:
        messages.error(
            request,
            "Token has expired or is invalid! Please request a new one",
        )
        return redirect("forgot_password")

    if request.method != "POST":
        form = ResetPasswordForm(instance=obj_token.user)
        return render(request, "reset_password.html", {"token": token, "form": form})

    form = ResetPasswordForm(request.POST, instance=obj_token.user)

    if form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
                obj_token.mark_as_used()
            send_password_changed_email.delay_on_commit(user.id)
            messages.success(request, "Password reset successfully")
            return redirect("sign_in")
        except Exception as e:
            messages.error(request, f"Error resetting password: {e!s}")
            return redirect("forgot_password")

    return render(request, "reset_password.html", {"token": token, "form": form})
